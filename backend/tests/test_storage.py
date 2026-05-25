"""Unit tests for the DuckDB storage layer."""

from __future__ import annotations

from typing import Any

import duckdb

from app.digest.builder import build_digest
from app.digest.models import GameDigest
from app.storage.db import (
    get_agenda,
    get_all_digests,
    get_game,
    list_games,
    query_history,
    save_agenda,
    save_game,
)


def _ingest(db: duckdb.DuckDBPyConnection, raw: dict[str, Any]) -> GameDigest:
    digest = build_digest(raw)
    save_game(db, digest)
    return digest


def test_save_and_get_game(
    in_memory_db: duckdb.DuckDBPyConnection, sample_raw_game: dict[str, Any]
) -> None:
    digest = _ingest(in_memory_db, sample_raw_game)
    retrieved = get_game(in_memory_db, digest.meta.game_id)
    assert retrieved is not None
    assert retrieved.meta.game_id == digest.meta.game_id
    assert retrieved.meta.patch == digest.meta.patch


def test_get_game_not_found(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    assert get_game(in_memory_db, "NONEXISTENT") is None


def test_list_games_empty(in_memory_db: duckdb.DuckDBPyConnection) -> None:
    assert list_games(in_memory_db) == []


def test_list_games_after_insert(
    in_memory_db: duckdb.DuckDBPyConnection, sample_raw_game: dict[str, Any]
) -> None:
    _ingest(in_memory_db, sample_raw_game)
    summaries = list_games(in_memory_db)
    assert len(summaries) == 1
    s = summaries[0]
    assert s["game_id"] == "EUW1_TEST123"
    assert s["patch"] == "14.10"
    assert s["result"] == "win"


def test_save_game_idempotent(
    in_memory_db: duckdb.DuckDBPyConnection, sample_raw_game: dict[str, Any]
) -> None:
    """Saving the same game twice should not duplicate rows."""
    _ingest(in_memory_db, sample_raw_game)
    _ingest(in_memory_db, sample_raw_game)
    assert len(list_games(in_memory_db)) == 1


def test_derived_lane_states_inserted(
    in_memory_db: duckdb.DuckDBPyConnection, sample_raw_game: dict[str, Any]
) -> None:
    _ingest(in_memory_db, sample_raw_game)
    count = in_memory_db.execute(
        "SELECT COUNT(*) FROM lane_states WHERE game_id = 'EUW1_TEST123'"
    ).fetchone()[0]
    assert count == 15  # 3 checkpoints × 5 lanes


def test_derived_objectives_inserted(
    in_memory_db: duckdb.DuckDBPyConnection, sample_raw_game: dict[str, Any]
) -> None:
    _ingest(in_memory_db, sample_raw_game)
    count = in_memory_db.execute(
        "SELECT COUNT(*) FROM objectives WHERE game_id = 'EUW1_TEST123'"
    ).fetchone()[0]
    assert count >= 1  # at least the dragon


def test_derived_fights_inserted(
    in_memory_db: duckdb.DuckDBPyConnection, sample_raw_game: dict[str, Any]
) -> None:
    _ingest(in_memory_db, sample_raw_game)
    count = in_memory_db.execute(
        "SELECT COUNT(*) FROM fights WHERE game_id = 'EUW1_TEST123'"
    ).fetchone()[0]
    assert count >= 1


def test_agenda_cache(
    in_memory_db: duckdb.DuckDBPyConnection, sample_raw_game: dict[str, Any]
) -> None:
    _ingest(in_memory_db, sample_raw_game)
    assert get_agenda(in_memory_db, "EUW1_TEST123") is None

    agenda_data = [
        {
            "rank": 1,
            "t": 900,
            "label": "fight",
            "title": "Test",
            "context": "ctx",
            "what_to_watch": "wtw",
        }
    ]
    save_agenda(in_memory_db, "EUW1_TEST123", agenda_data)

    cached = get_agenda(in_memory_db, "EUW1_TEST123")
    assert cached is not None
    assert cached[0]["rank"] == 1


def test_query_history_all(
    in_memory_db: duckdb.DuckDBPyConnection, sample_raw_game: dict[str, Any]
) -> None:
    _ingest(in_memory_db, sample_raw_game)
    results = query_history(in_memory_db)
    assert len(results) == 1


def test_query_history_patch_filter(
    in_memory_db: duckdb.DuckDBPyConnection, sample_raw_game: dict[str, Any]
) -> None:
    _ingest(in_memory_db, sample_raw_game)
    assert len(query_history(in_memory_db, patch="14.10")) == 1
    assert len(query_history(in_memory_db, patch="99.99")) == 0


def test_get_all_digests(
    in_memory_db: duckdb.DuckDBPyConnection, sample_raw_game: dict[str, Any]
) -> None:
    _ingest(in_memory_db, sample_raw_game)
    all_d = get_all_digests(in_memory_db)
    assert len(all_d) == 1
    assert all_d[0].meta.game_id == "EUW1_TEST123"
