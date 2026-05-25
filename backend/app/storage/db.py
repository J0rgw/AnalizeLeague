"""
DuckDB persistence layer.

Responsibilities:
  - Initialize the database schema on first run.
  - Persist GameDigest records as JSON.
  - Support historical Q&A queries across stored games.

DuckDB stores data at the path configured in settings.duckdb_path.
The /data directory is gitignored — it lives only on the local machine.
"""
from __future__ import annotations

import logging

import duckdb

from app.config import settings
from app.digest.models import GameDigest

logger = logging.getLogger(__name__)

_CREATE_GAMES_TABLE = """
CREATE TABLE IF NOT EXISTS games (
    game_id     VARCHAR PRIMARY KEY,
    patch       VARCHAR NOT NULL,
    recorded_at TIMESTAMP DEFAULT NOW(),
    digest_json JSON    NOT NULL
);
"""


def init_db() -> duckdb.DuckDBPyConnection:
    """
    Open (or create) the DuckDB database and ensure schema is up to date.

    Returns:
        An open DuckDBPyConnection. Caller is responsible for closing it.
    """
    # TODO (Phase 2): add migration strategy when schema evolves
    conn = duckdb.connect(settings.duckdb_path)
    conn.execute(_CREATE_GAMES_TABLE)
    logger.info("DuckDB initialized at %s", settings.duckdb_path)
    return conn


def save_game(conn: duckdb.DuckDBPyConnection, digest: GameDigest) -> None:
    """
    Persist a GameDigest to the games table.

    Args:
        conn:   An open DuckDBPyConnection (from init_db).
        digest: The GameDigest to persist.

    Raises:
        NotImplementedError: Phase 1 stub. Implement in Phase 2.
    """
    # TODO (Phase 2): INSERT OR REPLACE INTO games using digest.model_dump_json()
    raise NotImplementedError("save_game is a Phase 1 stub. Implement in Phase 2.")


def query_history(
    conn: duckdb.DuckDBPyConnection,
    *,
    patch: str | None = None,
    limit: int = 50,
) -> list[GameDigest]:
    """
    Retrieve historical GameDigest records for Q&A context.

    Args:
        conn:  An open DuckDBPyConnection.
        patch: Optional patch filter (e.g. "14.10"). None returns all patches.
        limit: Maximum number of records to return.

    Raises:
        NotImplementedError: Phase 1 stub. Implement in Phase 2.
    """
    # TODO (Phase 2): SELECT from games with optional WHERE patch = ? and LIMIT
    raise NotImplementedError("query_history is a Phase 1 stub. Implement in Phase 2.")
