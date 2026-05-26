"""
SQL validator and runner for the text-to-SQL Q&A feature.

The validator is the security boundary: a model-generated SELECT is only
executed against DuckDB after passing every check here. Treat any change
in this module as security-sensitive.

Allowed:
  - One top-level statement: SELECT ... or WITH ... SELECT ...
  - References only to whitelisted tables (games, lane_states, objectives, fights)
  - Implicit LIMIT injection if the query has none

Disallowed (rejected before execution):
  - Comments (-- or block)
  - Multiple statements (a single trailing semicolon is tolerated)
  - Any of the destructive keywords listed in _FORBIDDEN_KEYWORDS
  - References to tables outside the whitelist
"""

from __future__ import annotations

import logging
import re
from typing import Any

import duckdb

logger = logging.getLogger(__name__)

ALLOWED_TABLES: frozenset[str] = frozenset({"games", "lane_states", "objectives", "fights"})
MAX_LIMIT: int = 200

# Word-boundary matching prevents false positives like a column named "created_at"
# being confused with the CREATE keyword.
_FORBIDDEN_KEYWORDS: tuple[str, ...] = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "ATTACH",
    "COPY",
    "INSTALL",
    "LOAD",
    "PRAGMA",
    "EXPORT",
    "REPLACE",
    "TRUNCATE",
    "GRANT",
    "REVOKE",
    "VACUUM",
)

_TABLE_REF_PATTERN = re.compile(
    r"\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE,
)
_LIMIT_TAIL_PATTERN = re.compile(
    r"\bLIMIT\s+(\d+)(\s+OFFSET\s+\d+)?\s*;?\s*$",
    re.IGNORECASE,
)
_COMMENT_PATTERN = re.compile(r"(--|/\*|\*/)")


class SqlValidationError(ValueError):
    """Raised when a model-generated SQL string fails the validator."""


def validate_select(sql: str) -> str:
    """
    Validate and normalize a SELECT-only SQL string.

    Returns the cleaned SQL ready for execution (with LIMIT enforced).
    Raises SqlValidationError if any rule is violated.
    """
    if not isinstance(sql, str) or not sql.strip():
        raise SqlValidationError("Empty SQL")

    cleaned = sql.strip()
    # Strip a single trailing semicolon; multiple semicolons stay and trip the check below.
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].rstrip()

    if ";" in cleaned:
        raise SqlValidationError("Multiple statements are not allowed")

    if _COMMENT_PATTERN.search(cleaned):
        raise SqlValidationError("SQL comments are not allowed")

    upper = cleaned.upper()
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        raise SqlValidationError("Only SELECT or WITH...SELECT queries are allowed")

    for kw in _FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{kw}\b", upper):
            raise SqlValidationError(f"Forbidden keyword: {kw}")

    referenced = {m.group(1).lower() for m in _TABLE_REF_PATTERN.finditer(cleaned)}
    # A WITH-CTE introduces names that look like table references in FROM clauses.
    # Extract CTE names so we can allow them.
    cte_names = _extract_cte_names(cleaned)
    unknown = referenced - ALLOWED_TABLES - cte_names
    if unknown:
        raise SqlValidationError(f"Reference to disallowed table(s): {', '.join(sorted(unknown))}")

    return _enforce_limit(cleaned)


def _extract_cte_names(sql: str) -> set[str]:
    """Pick up names declared in a leading WITH clause: `WITH a AS (...), b AS (...)`."""
    upper = sql.upper()
    if not upper.startswith("WITH"):
        return set()
    # Scan top-level `name AS (` declarations, respecting parenthesis depth.
    names: set[str] = set()
    i = len("WITH")
    depth = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        if ch == "(":
            depth += 1
            i += 1
            continue
        if ch == ")":
            depth -= 1
            i += 1
            continue
        if depth == 0:
            # At depth 0 we expect: <identifier> AS (...
            m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s+AS\s*\(", sql[i:], re.IGNORECASE)
            if m:
                names.add(m.group(1).lower())
                i += m.end()
                depth = 1  # we just consumed the opening paren
                continue
            # Reached the body SELECT — stop scanning.
            if re.match(r"\s*SELECT\b", sql[i:], re.IGNORECASE):
                break
        i += 1
    return names


def _enforce_limit(sql: str) -> str:
    """Append LIMIT MAX_LIMIT if absent; cap to MAX_LIMIT if higher."""
    m = _LIMIT_TAIL_PATTERN.search(sql)
    if m is None:
        return f"{sql} LIMIT {MAX_LIMIT}"
    existing = int(m.group(1))
    if existing <= MAX_LIMIT:
        return sql
    offset_clause = m.group(2) or ""
    return _LIMIT_TAIL_PATTERN.sub(f"LIMIT {MAX_LIMIT}{offset_clause}", sql)


def run_safe_select(
    conn: duckdb.DuckDBPyConnection,
    sql: str,
) -> tuple[list[str], list[tuple[Any, ...]]]:
    """
    Execute an already-validated SELECT on a read-only cursor.

    The caller MUST pass SQL that has been through `validate_select`.
    A fresh cursor is used so the parent connection's transaction state
    is unaffected; DuckDB cursors share the database catalog but isolate
    statement execution.
    """
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        columns = [d[0] for d in (cursor.description or [])]
        rows: list[tuple[Any, ...]] = cursor.fetchall()
        return columns, rows
    finally:
        cursor.close()


# Human-readable schema description fed to the LLM as part of the SQL-generation prompt.
SCHEMA_DESCRIPTION: str = """\
Tables (DuckDB):

games (
  game_id     VARCHAR PRIMARY KEY,
  patch       VARCHAR,         -- e.g. '14.10'
  side        VARCHAR,         -- 'blue' | 'red' (analyzed team's side)
  result      VARCHAR,         -- 'win' | 'loss'
  duration_s  INTEGER,
  recorded_at TIMESTAMP,
  digest_json JSON,
  agenda_json JSON
)

lane_states (
  game_id   VARCHAR,
  at_min    INTEGER,           -- 8, 14, or 20
  lane      VARCHAR,           -- 'top' | 'jng' | 'mid' | 'bot' | 'sup'
  gold_diff INTEGER,           -- positive = analyzed team ahead
  cs_diff   INTEGER,
  xp_diff   INTEGER,
  kills     INTEGER
)

objectives (
  game_id          VARCHAR,
  t                INTEGER,    -- seconds
  type             VARCHAR,    -- 'baron' | 'dragon' | 'herald' | 'tower' | 'inhibitor' | 'void_grubs'
  subtype          VARCHAR,    -- e.g. 'infernal', 'outer', '' for none
  team             VARCHAR,    -- 'blue' | 'red'
  gold_diff_at_evt INTEGER,
  tradeoff         VARCHAR
)

fights (
  game_id       VARCHAR,
  t             INTEGER,       -- seconds
  where_zone    VARCHAR,       -- e.g. 'baron_pit', 'mid_lane'
  kills_for     INTEGER,
  kills_against INTEGER,
  gold_swing    INTEGER,
  led_to        VARCHAR        -- subsequent objective, '' if none
)
"""
