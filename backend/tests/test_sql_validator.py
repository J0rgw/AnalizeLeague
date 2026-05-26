"""
Unit tests for the SQL validator that gates model-generated Q&A queries.

The validator is the security boundary for the text-to-SQL feature, so the
tests focus on the rejection rules (forbidden keywords, multiple statements,
comments, off-whitelist tables) and the LIMIT enforcement.
"""

from __future__ import annotations

import pytest

from app.llm.sql import MAX_LIMIT, SqlValidationError, validate_select

# ── Acceptances ───────────────────────────────────────────────────────────────


def test_accepts_basic_select_and_appends_limit() -> None:
    out = validate_select("SELECT game_id FROM games")
    assert out == f"SELECT game_id FROM games LIMIT {MAX_LIMIT}"


def test_accepts_select_with_join_on_allowed_tables() -> None:
    sql = """
        SELECT g.game_id, AVG(ls.gold_diff) AS avg_diff
        FROM games g
        JOIN lane_states ls ON ls.game_id = g.game_id
        WHERE ls.at_min = 14
        GROUP BY g.game_id
    """
    out = validate_select(sql)
    assert "LIMIT" in out.upper()


def test_accepts_with_cte_referencing_allowed_table() -> None:
    sql = (
        "WITH late_fights AS (SELECT * FROM fights WHERE t > 1500) "
        "SELECT game_id, COUNT(*) FROM late_fights GROUP BY game_id"
    )
    out = validate_select(sql)
    assert out.upper().endswith(f"LIMIT {MAX_LIMIT}")


def test_accepts_existing_limit_under_cap_and_preserves_it() -> None:
    out = validate_select("SELECT game_id FROM games LIMIT 50")
    assert out == "SELECT game_id FROM games LIMIT 50"


def test_caps_oversized_limit_to_max() -> None:
    out = validate_select("SELECT game_id FROM games LIMIT 9999")
    assert out.endswith(f"LIMIT {MAX_LIMIT}")


def test_preserves_offset_when_capping_limit() -> None:
    out = validate_select("SELECT game_id FROM games LIMIT 9999 OFFSET 30")
    assert out.endswith(f"LIMIT {MAX_LIMIT} OFFSET 30")


def test_tolerates_single_trailing_semicolon() -> None:
    out = validate_select("SELECT game_id FROM games;")
    assert out.endswith(f"LIMIT {MAX_LIMIT}")


# ── Rejections — destructive keywords ─────────────────────────────────────────


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE games",
        "DELETE FROM games WHERE 1=1",
        "INSERT INTO games VALUES (1)",
        "UPDATE games SET patch='x'",
        "ALTER TABLE games ADD COLUMN x INT",
        "CREATE TABLE evil (id INT)",
        "ATTACH 'evil.db' AS evil",
        "COPY games TO 'leak.csv'",
        "PRAGMA database_list",
        "INSTALL httpfs",
        "LOAD httpfs",
        "EXPORT DATABASE 'leak/'",
    ],
)
def test_rejects_destructive_top_level_statements(sql: str) -> None:
    with pytest.raises(SqlValidationError):
        validate_select(sql)


def test_rejects_destructive_keyword_inside_otherwise_select() -> None:
    # Even if wrapped, forbidden keywords are rejected (defense in depth).
    with pytest.raises(SqlValidationError):
        validate_select("SELECT * FROM games; DROP TABLE games")


# ── Rejections — multi-statement & comments ───────────────────────────────────


def test_rejects_multiple_statements() -> None:
    with pytest.raises(SqlValidationError):
        validate_select("SELECT 1; SELECT 2")


def test_rejects_line_comment() -> None:
    with pytest.raises(SqlValidationError):
        validate_select("SELECT game_id FROM games -- sneaky")


def test_rejects_block_comment() -> None:
    with pytest.raises(SqlValidationError):
        validate_select("SELECT /* hidden */ game_id FROM games")


# ── Rejections — non-SELECT entry points ──────────────────────────────────────


@pytest.mark.parametrize("sql", ["EXPLAIN SELECT 1", "DESCRIBE games", ""])
def test_rejects_non_select_entry_points(sql: str) -> None:
    with pytest.raises(SqlValidationError):
        validate_select(sql)


# ── Rejections — disallowed tables ────────────────────────────────────────────


def test_rejects_query_against_unknown_table() -> None:
    with pytest.raises(SqlValidationError):
        validate_select("SELECT * FROM information_schema.tables")


def test_rejects_join_to_unknown_table() -> None:
    sql = (
        "SELECT g.game_id FROM games g JOIN information_schema.columns c ON c.table_name = 'games'"
    )
    with pytest.raises(SqlValidationError):
        validate_select(sql)
