"""
Shared pytest fixtures.

Fixtures:
  sample_raw_game  — minimal Riot API match + timeline dict, complete enough for build_digest
  in_memory_db     — fresh DuckDB connection with schema applied
  test_client      — FastAPI TestClient with in-memory DuckDB injected
"""

from __future__ import annotations

from typing import Any

import duckdb
import pytest
from fastapi.testclient import TestClient

from app.api.main import app

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
        pframes[str(pid)] = {
            "participantId": pid,
            "totalGold": gold_base + relative_pid * 50 + team_bonus,
            "minionsKilled": (t_ms // 60_000) * 6 + pid,
            "jungleMinionsKilled": 0 if pid not in (2, 7) else (t_ms // 60_000) * 4,
            "xp": gold_base * 2 + pid * 30,
            "position": {"x": 3000 + pid * 200, "y": 3000 + pid * 200},
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
    camp_event = {
        "type": "MONSTER_KILL",
        "timestamp": 90_000,  # 1:30
        "monsterType": "BLUE_SENTINEL",
        "killerId": 2,
        "position": {"x": 3500, "y": 8000},
    }

    frames = [
        _make_frame(0, pids),
        *[
            _make_frame(
                m * 60_000,
                pids,
                gold_base=500 + m * 100,
                events=(
                    [camp_event]
                    if m == 1
                    else [dragon_event]
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
