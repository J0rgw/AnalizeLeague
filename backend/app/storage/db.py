"""
DuckDB persistence layer.

Schema:
  games        — one row per game: digest JSON + optional agenda JSON
  lane_states  — derived, queryable per-lane per-minute data
  objectives   — derived, queryable objective events
  fights       — derived, queryable fight events

The derived tables enable cross-game SQL queries for the Q&A feature.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import duckdb

from app.config import settings
from app.digest.models import GameDigest

logger = logging.getLogger(__name__)

# ── Schema ────────────────────────────────────────────────────────────────────

_DDL_GAMES = """
CREATE TABLE IF NOT EXISTS games (
    game_id     VARCHAR PRIMARY KEY,
    patch       VARCHAR NOT NULL,
    side        VARCHAR NOT NULL DEFAULT 'blue',
    result      VARCHAR NOT NULL DEFAULT 'unknown',
    duration_s  INTEGER NOT NULL DEFAULT 0,
    recorded_at TIMESTAMP DEFAULT NOW(),
    digest_json JSON    NOT NULL,
    agenda_json JSON
);
"""

_DDL_LANE_STATES = """
CREATE TABLE IF NOT EXISTS lane_states (
    game_id   VARCHAR NOT NULL,
    at_min    INTEGER NOT NULL,
    lane      VARCHAR NOT NULL,
    gold_diff INTEGER NOT NULL,
    cs_diff   INTEGER NOT NULL,
    xp_diff   INTEGER NOT NULL,
    kills     INTEGER NOT NULL,
    PRIMARY KEY (game_id, at_min, lane)
);
"""

_DDL_OBJECTIVES = """
CREATE TABLE IF NOT EXISTS objectives (
    game_id          VARCHAR NOT NULL,
    t                INTEGER NOT NULL,
    type             VARCHAR NOT NULL,
    subtype          VARCHAR NOT NULL,
    team             VARCHAR NOT NULL,
    gold_diff_at_evt INTEGER NOT NULL,
    tradeoff         VARCHAR NOT NULL
);
"""

_DDL_FIGHTS = """
CREATE TABLE IF NOT EXISTS fights (
    game_id       VARCHAR NOT NULL,
    t             INTEGER NOT NULL,
    where_zone    VARCHAR NOT NULL,
    kills_for     INTEGER NOT NULL,
    kills_against INTEGER NOT NULL,
    gold_swing    INTEGER NOT NULL,
    led_to        VARCHAR NOT NULL
);
"""

# ── Migration: add columns that may be absent in older DBs ───────────────────

_MIGRATIONS: list[tuple[str, str]] = [
    ("games", "side        VARCHAR NOT NULL DEFAULT 'blue'"),
    ("games", "result      VARCHAR NOT NULL DEFAULT 'unknown'"),
    ("games", "duration_s  INTEGER NOT NULL DEFAULT 0"),
    ("games", "agenda_json JSON"),
]


def _migrate(conn: duckdb.DuckDBPyConnection) -> None:
    existing: set[str] = set()
    try:
        rows = conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'games'"
        ).fetchall()
        existing = {r[0] for r in rows}
    except Exception:
        return  # table doesn't exist yet, DDL will create it
    for _table, col_def in _MIGRATIONS:
        col_name = col_def.split()[0]
        if col_name not in existing:
            try:
                conn.execute(f"ALTER TABLE games ADD COLUMN {col_def}")
                logger.info("Migration: added column games.%s", col_name)
            except Exception as exc:
                logger.warning("Migration skipped (%s): %s", col_name, exc)


# ── Public API ────────────────────────────────────────────────────────────────


def init_db() -> duckdb.DuckDBPyConnection:
    """Open (or create) the DuckDB database and ensure schema is current."""
    db_path = settings.duckdb_path
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(db_path)
    _migrate(conn)
    conn.execute(_DDL_GAMES)
    conn.execute(_DDL_LANE_STATES)
    conn.execute(_DDL_OBJECTIVES)
    conn.execute(_DDL_FIGHTS)
    logger.info("DuckDB ready: %s", db_path)
    return conn


def save_game(conn: duckdb.DuckDBPyConnection, digest: GameDigest) -> None:
    """Persist a GameDigest (and derived rows) to DuckDB."""
    gid = digest.meta.game_id
    digest_json = digest.model_dump_json()

    conn.execute(
        """
        INSERT INTO games (game_id, patch, side, result, duration_s, digest_json)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (game_id) DO UPDATE SET
            patch       = EXCLUDED.patch,
            side        = EXCLUDED.side,
            result      = EXCLUDED.result,
            duration_s  = EXCLUDED.duration_s,
            digest_json = EXCLUDED.digest_json
        """,
        [
            gid,
            digest.meta.patch,
            digest.meta.side,
            digest.meta.result,
            digest.meta.duration_s,
            digest_json,
        ],
    )

    # Derived table: lane_states
    conn.execute("DELETE FROM lane_states WHERE game_id = ?", [gid])
    ls_rows = [
        [gid, ls.at_min, ls.lane, ls.gold_diff, ls.cs_diff, ls.xp_diff, ls.kills]
        for ls in digest.lane_states
    ]
    if ls_rows:
        conn.executemany("INSERT INTO lane_states VALUES (?,?,?,?,?,?,?)", ls_rows)

    # Derived table: objectives
    conn.execute("DELETE FROM objectives WHERE game_id = ?", [gid])
    obj_rows = [
        [gid, o.t, o.type, o.subtype, o.team, o.gold_diff_at_event, o.tradeoff]
        for o in digest.objectives
    ]
    if obj_rows:
        conn.executemany("INSERT INTO objectives VALUES (?,?,?,?,?,?,?)", obj_rows)

    # Derived table: fights
    conn.execute("DELETE FROM fights WHERE game_id = ?", [gid])
    fight_rows = [
        [gid, f.t, f.where, f.kills_for, f.kills_against, f.gold_swing, f.led_to]
        for f in digest.fights
    ]
    if fight_rows:
        conn.executemany("INSERT INTO fights VALUES (?,?,?,?,?,?,?)", fight_rows)

    logger.info("Saved game %s to DuckDB", gid)


def get_game(conn: duckdb.DuckDBPyConnection, game_id: str) -> GameDigest | None:
    """Return a stored GameDigest by ID, or None if not found."""
    row = conn.execute("SELECT digest_json FROM games WHERE game_id = ?", [game_id]).fetchone()
    if row is None:
        return None
    return GameDigest.model_validate_json(row[0])


def list_games(conn: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """Return summary rows for all stored games (for the game selector UI)."""
    rows = conn.execute(
        "SELECT game_id, patch, side, result, duration_s FROM games ORDER BY recorded_at DESC"
    ).fetchall()
    return [
        {
            "game_id": r[0],
            "patch": r[1],
            "side": r[2],
            "result": r[3],
            "duration_s": r[4],
        }
        for r in rows
    ]


def save_agenda(
    conn: duckdb.DuckDBPyConnection,
    game_id: str,
    agenda: list[dict[str, Any]],
) -> None:
    """Cache a generated agenda for a game to avoid re-generating."""
    conn.execute(
        "UPDATE games SET agenda_json = ? WHERE game_id = ?",
        [json.dumps(agenda), game_id],
    )


def get_agenda(conn: duckdb.DuckDBPyConnection, game_id: str) -> list[dict[str, Any]] | None:
    """Return a cached agenda, or None if not yet generated."""
    row = conn.execute("SELECT agenda_json FROM games WHERE game_id = ?", [game_id]).fetchone()
    if row is None or row[0] is None:
        return None
    raw = row[0]
    data: list[dict[str, Any]] = json.loads(raw) if isinstance(raw, str) else raw
    return data


def get_all_digests(conn: duckdb.DuckDBPyConnection, *, limit: int = 10) -> list[GameDigest]:
    """Return the most recent stored digests (for Q&A context)."""
    rows = conn.execute(
        "SELECT digest_json FROM games ORDER BY recorded_at DESC LIMIT ?", [limit]
    ).fetchall()
    return [GameDigest.model_validate_json(r[0]) for r in rows]


def query_history(
    conn: duckdb.DuckDBPyConnection,
    *,
    patch: str | None = None,
    limit: int = 50,
) -> list[GameDigest]:
    """Retrieve historical GameDigest records, optionally filtered by patch."""
    if patch:
        rows = conn.execute(
            "SELECT digest_json FROM games WHERE patch = ? ORDER BY recorded_at DESC LIMIT ?",
            [patch, limit],
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT digest_json FROM games ORDER BY recorded_at DESC LIMIT ?", [limit]
        ).fetchall()
    return [GameDigest.model_validate_json(r[0]) for r in rows]
