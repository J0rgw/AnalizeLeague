"""Unit tests for the GRID streaming JSONL parser."""

from __future__ import annotations

import orjson

from app.ingest.grid import _DEFAULT_RELEVANT, stream_grid_events


def _lines(*events: dict) -> list[bytes]:
    return [orjson.dumps(e) + b"\n" for e in events]


def test_yields_relevant_events() -> None:
    events = [
        {"type": "champion_kill", "timestamp": 1000, "killerId": 1},
        {"type": "champion_level_up", "timestamp": 1500, "participantId": 2},  # filtered
        {"type": "epic_monster_killed", "timestamp": 2000, "monsterType": "BARON"},
    ]
    result = list(stream_grid_events(_lines(*events)))
    assert len(result) == 2
    assert result[0]["type"] == "champion_kill"
    assert result[1]["type"] == "epic_monster_killed"


def test_filters_by_custom_types() -> None:
    events = [
        {"type": "champion_kill", "timestamp": 1000},
        {"type": "epic_monster_killed", "timestamp": 2000},
    ]
    result = list(
        stream_grid_events(_lines(*events), event_types=frozenset({"epic_monster_killed"}))
    )
    assert len(result) == 1
    assert result[0]["type"] == "epic_monster_killed"


def test_empty_type_set_yields_all() -> None:
    events = [
        {"type": "champion_kill"},
        {"type": "ward_placed"},
        {"type": "anything_else"},
    ]
    result = list(stream_grid_events(_lines(*events), event_types=frozenset()))
    assert len(result) == 3


def test_skips_blank_lines() -> None:
    lines: list[bytes] = [
        b"\n",
        b"  \n",
        orjson.dumps({"type": "champion_kill"}) + b"\n",
        b"\n",
    ]
    result = list(stream_grid_events(lines))
    assert len(result) == 1


def test_skips_malformed_json() -> None:
    lines: list[bytes] = [
        b"{not valid json}\n",
        orjson.dumps({"type": "champion_kill"}) + b"\n",
    ]
    result = list(stream_grid_events(lines))
    assert len(result) == 1


def test_case_insensitive_type_matching() -> None:
    """GRID events may use lowercase type; matching should be case-insensitive."""
    events = [{"type": "Champion_Kill"}, {"type": "CHAMPION_KILL"}]
    result = list(stream_grid_events(_lines(*events)))
    assert len(result) == 2


def test_default_relevant_types_are_defined() -> None:
    assert "champion_kill" in _DEFAULT_RELEVANT
    assert "epic_monster_killed" in _DEFAULT_RELEVANT
    assert "ward_placed" in _DEFAULT_RELEVANT


def test_accepts_raw_io_base() -> None:
    """stream_grid_events accepts any iterable of bytes, including file-like objects."""
    data = b'{"type": "champion_kill"}\n{"type": "ward_placed"}\n'
    lines = [line + b"\n" for line in data.splitlines()]
    result = list(stream_grid_events(lines))
    assert len(result) == 2
