"""
Shared pytest fixtures.

Fixtures:
  sample_raw_game  — minimal Riot API match + timeline dict, complete enough for build_digest
  in_memory_db     — fresh DuckDB connection with schema applied
  test_client      — FastAPI TestClient with in-memory DuckDB injected
  _no_network_ddragon (autouse) — stub Data Dragon so resolve_champion_name
    never makes an HTTP request during tests.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import duckdb
import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.digest import champions as champions_mod


@pytest.fixture(autouse=True)
def _no_network_ddragon(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pytest.TempPathFactory,
) -> Iterator[None]:
    """
    Tests must never reach the Data Dragon CDN, AND must not share a disk
    cache across tests (a cached champion.json from one test would silently
    satisfy another test that's supposed to exercise the no-network path).
    """
    monkeypatch.setattr(
        champions_mod,
        "_fetch_champion_json",
        lambda _version: None,
    )
    # Redirect the disk cache to a per-test temp dir.
    monkeypatch.setattr(champions_mod, "_CACHE_DIR", tmp_path / "ddragon")  # type: ignore[arg-type]
    champions_mod.clear_cache()
    yield
    champions_mod.clear_cache()


# ── Minimal Riot API fixture ──────────────────────────────────────────────────


def _make_participant(
    pid: int,
    team_id: int,
    position: str,
    champion: str,
) -> dict[str, Any]:
    return {
        "participantId": pid,
        "teamId": team_id,
        "teamPosition": position,
        "championName": champion,
        "kills": 0,
        "deaths": 0,
        "assists": 0,
    }


# Realistic early-clear positions for the junglers in this fixture, so that
# _build_jungle_path's position-to-camp inference picks up a meaningful path.
_BLUE_JNG_POS_BY_MIN: dict[int, tuple[int, int]] = {
    1: (3_850, 7_950),  # blue_buff
    2: (3_900, 6_500),  # wolves
    3: (6_900, 5_500),  # raptors
    4: (2_150, 8_400),  # gromp
}
_RED_JNG_POS_BY_MIN: dict[int, tuple[int, int]] = {
    1: (10_950, 6_850),  # blue_buff (red side)
    2: (10_800, 8_350),  # wolves (red side)
    3: (7_900, 9_500),  # raptors (red side)
    4: (12_750, 6_400),  # gromp (red side)
}


def _position_for(pid: int, t_ms: int) -> tuple[int, int]:
    minute = t_ms // 60_000
    if pid == 2 and minute in _BLUE_JNG_POS_BY_MIN:
        return _BLUE_JNG_POS_BY_MIN[minute]
    if pid == 7 and minute in _RED_JNG_POS_BY_MIN:
        return _RED_JNG_POS_BY_MIN[minute]
    # Default: generic mid-map position scaled by pid for variety.
    return 3_000 + pid * 200, 3_000 + pid * 200


def _make_frame(
    t_ms: int,
    pids: list[int],
    gold_base: int = 500,
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    pframes: dict[str, Any] = {}
    for pid in pids:
        # Normalise pid to 1-5 within each team so blue always has more gold than red
        relative_pid = pid if pid <= 5 else pid - 5
        team_bonus = 300 if pid <= 5 else 0
        x, y = _position_for(pid, t_ms)
        pframes[str(pid)] = {
            "participantId": pid,
            "totalGold": gold_base + relative_pid * 50 + team_bonus,
            "minionsKilled": (t_ms // 60_000) * 6 + pid,
            "jungleMinionsKilled": 0 if pid not in (2, 7) else (t_ms // 60_000) * 4,
            "xp": gold_base * 2 + pid * 30,
            "position": {"x": x, "y": y},
        }
    return {"timestamp": t_ms, "participantFrames": pframes, "events": events or []}


@pytest.fixture
def sample_raw_game() -> dict[str, Any]:
    """Minimal but valid Riot API match + timeline for build_digest testing."""
    participants = [
        _make_participant(1, 100, "TOP", "Darius"),
        _make_participant(2, 100, "JUNGLE", "Vi"),
        _make_participant(3, 100, "MIDDLE", "Syndra"),
        _make_participant(4, 100, "BOTTOM", "Jinx"),
        _make_participant(5, 100, "UTILITY", "Thresh"),
        _make_participant(6, 200, "TOP", "Garen"),
        _make_participant(7, 200, "JUNGLE", "Lee Sin"),
        _make_participant(8, 200, "MIDDLE", "Zed"),
        _make_participant(9, 200, "BOTTOM", "Caitlyn"),
        _make_participant(10, 200, "UTILITY", "Lux"),
    ]
    pids = list(range(1, 11))

    # Events: a fight at minute 15, a dragon at minute 10
    fight_events = [
        {
            "type": "CHAMPION_KILL",
            "timestamp": 15 * 60_000 + 5_000,
            "killerId": 3,
            "victimId": 8,
            "position": {"x": 7500, "y": 7500},
            "assistingParticipantIds": [4],
        },
        {
            "type": "CHAMPION_KILL",
            "timestamp": 15 * 60_000 + 8_000,
            "killerId": 4,
            "victimId": 9,
            "position": {"x": 7600, "y": 7400},
            "assistingParticipantIds": [],
        },
    ]
    dragon_event = {
        "type": "ELITE_MONSTER_KILL",
        "timestamp": 10 * 60_000,
        "monsterType": "DRAGON",
        "monsterSubType": "FIRE_DRAGON",
        "killerTeamId": 100,
        "killerId": 2,
    }
    tower_event = {
        "type": "BUILDING_KILL",
        "timestamp": 18 * 60_000,
        "teamId": 200,  # red team's tower was destroyed
        "buildingType": "TOWER_BUILDING",
        "towerType": "OUTER_TURRET",
        "laneType": "MID_LANE",
        "killerId": 3,
    }
    # NOTE: the Riot timeline does NOT emit a "MONSTER_KILL" event for normal
    # camps — only ELITE_MONSTER_KILL for dragon/herald/baron/grubs.
    # _build_jungle_path reconstructs the early clear from jungleMinionsKilled
    # increments + jungler positions instead.
    frames = [
        _make_frame(0, pids),
        *[
            _make_frame(
                m * 60_000,
                pids,
                gold_base=500 + m * 100,
                events=(
                    [dragon_event]
                    if m == 10
                    else fight_events
                    if m == 15
                    else [tower_event]
                    if m == 18
                    else []
                ),
            )
            for m in range(1, 26)
        ],
    ]

    return {
        "game_id": "EUW1_TEST123",
        "match": {
            "metadata": {"matchId": "EUW1_TEST123"},
            "info": {
                "gameDuration": 25 * 60,
                "gameVersion": "14.10.123.4567",
                "participants": participants,
                "teams": [
                    {
                        "teamId": 100,
                        "win": True,
                        "bans": [{"championId": 157}] * 5,
                        "objectives": {},
                    },
                    {
                        "teamId": 200,
                        "win": False,
                        "bans": [{"championId": 238}] * 5,
                        "objectives": {},
                    },
                ],
            },
        },
        "timeline": {
            "metadata": {"matchId": "EUW1_TEST123"},
            "info": {"frameInterval": 60_000, "frames": frames},
        },
    }


# ── DuckDB in-memory fixture ──────────────────────────────────────────────────


@pytest.fixture
def in_memory_db() -> duckdb.DuckDBPyConnection:
    """Fresh in-memory DuckDB with schema applied."""
    import duckdb as _duckdb

    from app.storage import db as dbmod

    conn = _duckdb.connect(":memory:")
    # Apply all DDL
    conn.execute(dbmod._DDL_GAMES)
    conn.execute(dbmod._DDL_LANE_STATES)
    conn.execute(dbmod._DDL_OBJECTIVES)
    conn.execute(dbmod._DDL_FIGHTS)
    return conn


# ── FastAPI test client ───────────────────────────────────────────────────────


@pytest.fixture
def test_client(in_memory_db: duckdb.DuckDBPyConnection) -> TestClient:
    """TestClient with in-memory DuckDB injected into app.state."""
    app.state.db = in_memory_db
    return TestClient(app, raise_server_exceptions=True)
