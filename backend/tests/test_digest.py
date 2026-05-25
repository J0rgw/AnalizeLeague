"""
Unit tests for the digest builder.

All tests use the sample_raw_game fixture from conftest.py, which is a
minimal but complete Riot API match + timeline without any network calls.
"""

from __future__ import annotations

from typing import Any

from app.digest.builder import _position_to_zone, build_digest
from app.digest.models import GameDigest


def test_build_digest_returns_game_digest(sample_raw_game: dict[str, Any]) -> None:
    digest = build_digest(sample_raw_game)
    assert isinstance(digest, GameDigest)


def test_meta_fields(sample_raw_game: dict[str, Any]) -> None:
    digest = build_digest(sample_raw_game)
    assert digest.meta.game_id == "EUW1_TEST123"
    assert digest.meta.patch == "14.10"
    assert digest.meta.duration_s == 25 * 60
    assert digest.meta.side == "blue"
    assert digest.meta.result == "win"


def test_draft_champions(sample_raw_game: dict[str, Any]) -> None:
    digest = build_digest(sample_raw_game)
    assert digest.draft.blue.top == "Darius"
    assert digest.draft.blue.jng == "Vi"
    assert digest.draft.blue.mid == "Syndra"
    assert digest.draft.blue.bot == "Jinx"
    assert digest.draft.blue.sup == "Thresh"
    assert digest.draft.red.top == "Garen"
    assert digest.draft.red.jng == "Lee Sin"


def test_lane_states_populated(sample_raw_game: dict[str, Any]) -> None:
    digest = build_digest(sample_raw_game)
    # Three checkpoints × five lanes = 15 states
    assert len(digest.lane_states) == 15
    checkpoints = {ls.at_min for ls in digest.lane_states}
    assert checkpoints == {8, 14, 20}
    lanes = {ls.lane for ls in digest.lane_states}
    assert lanes == {"top", "jng", "mid", "bot", "sup"}


def test_blue_team_gold_advantage(sample_raw_game: dict[str, Any]) -> None:
    """Blue team has a bonus in the fixture; gold diffs should be positive."""
    digest = build_digest(sample_raw_game)
    mid_14 = next(
        (ls for ls in digest.lane_states if ls.at_min == 14 and ls.lane == "mid"),
        None,
    )
    assert mid_14 is not None
    assert mid_14.gold_diff > 0  # blue mid (Syndra, pid=3) ahead of red mid (Zed, pid=8)


def test_team_gold_diff_by_min_length(sample_raw_game: dict[str, Any]) -> None:
    digest = build_digest(sample_raw_game)
    # 25-minute game → 26 entries (minutes 0–25)
    assert len(digest.team_gold_diff_by_min) >= 25


def test_fight_detected(sample_raw_game: dict[str, Any]) -> None:
    digest = build_digest(sample_raw_game)
    assert len(digest.fights) >= 1
    fight = digest.fights[0]
    # Two kills at ~15:05 and ~15:08 → same fight cluster
    assert fight.kills_for + fight.kills_against == 2
    assert "Syndra" in fight.players_near or "Jinx" in fight.players_near


def test_dragon_objective(sample_raw_game: dict[str, Any]) -> None:
    digest = build_digest(sample_raw_game)
    dragons = [o for o in digest.objectives if o.type == "dragon"]
    assert len(dragons) == 1
    assert dragons[0].team == "blue"
    assert dragons[0].subtype == "infernal"
    assert dragons[0].t == 10 * 60


def test_tower_objective(sample_raw_game: dict[str, Any]) -> None:
    digest = build_digest(sample_raw_game)
    towers = [o for o in digest.objectives if o.type == "tower"]
    assert len(towers) == 1
    assert towers[0].team == "blue"  # red's tower was destroyed by blue


def test_jungle_path_blue(sample_raw_game: dict[str, Any]) -> None:
    digest = build_digest(sample_raw_game)
    # Vi (pid=2, blue jungler) cleared blue_buff at 1:30
    assert "blue_buff" in digest.jungle_path.blue


def test_bans_populated(sample_raw_game: dict[str, Any]) -> None:
    digest = build_digest(sample_raw_game)
    assert len(digest.draft.bans.blue) == 5
    assert len(digest.draft.bans.red) == 5


def test_red_side_analysis(sample_raw_game: dict[str, Any]) -> None:
    digest = build_digest(sample_raw_game, analyzed_side="red")
    assert digest.meta.side == "red"
    assert digest.meta.result == "loss"


def test_position_to_zone() -> None:

    assert _position_to_zone(5000, 10500) == "baron_pit"
    assert _position_to_zone(10000, 4500) == "dragon_pit"
    assert _position_to_zone(7500, 7500) == "mid_lane"
    assert _position_to_zone(1000, 13000) == "top_lane"
    assert _position_to_zone(13000, 1000) == "bot_lane"
