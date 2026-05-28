r"""
Seed script: insert a fully synthetic GameDigest into DuckDB.

Builds a GameDigest in memory (no Riot API, no network) and saves it via the
storage layer, so the rest of the system (/games, /debrief, /query) can be
exercised end-to-end without credentials.

Usage (run from /backend):
    uv run python scripts/seed_fake.py
    uv run python scripts/seed_fake.py --game-id EUW1_FAKE002 --side red --result loss

The default ID matches the API's Riot-match-ID pattern (^[A-Z]{2,4}\d{1,3}_[A-Z0-9]+$),
so /games/{id}/digest will accept it.
"""

from __future__ import annotations

import argparse
import logging
import sys

from app.digest.models import (
    Draft,
    DraftBans,
    DraftSide,
    Fight,
    GameDigest,
    GameMeta,
    JunglePath,
    LaneState,
    Objective,
    Recall,
)
from app.storage.db import init_db, save_game

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("seed_fake")


def _build_fake_digest(game_id: str, side: str, result: str) -> GameDigest:
    """Construct a plausible 28-minute scrim digest for the given side/result."""

    sign = 1 if side == "blue" else -1

    meta = GameMeta(
        game_id=game_id,
        patch="14.10",
        duration_s=28 * 60,
        side=side,
        result=result,
    )

    draft = Draft(
        blue=DraftSide(top="Darius", jng="Vi", mid="Syndra", bot="Jinx", sup="Thresh"),
        red=DraftSide(top="Garen", jng="Lee Sin", mid="Zed", bot="Caitlyn", sup="Lux"),
        bans=DraftBans(
            blue=["Yasuo", "Yone", "Kaisa", "Ahri", "K'Sante"],
            red=["Briar", "Hwei", "Senna", "Nautilus", "Aatrox"],
        ),
    )

    # Lane states at 8/14/20/25 — positive means analyzed side ahead.
    lane_states: list[LaneState] = []
    checkpoints = [
        (8, {"top": -200, "jng": 150, "mid": 450, "bot": 300, "sup": 50}),
        (14, {"top": -350, "jng": 400, "mid": 900, "bot": 600, "sup": 120}),
        (20, {"top": -100, "jng": 700, "mid": 1500, "bot": 1100, "sup": 250}),
        (25, {"top": 250, "jng": 1100, "mid": 2200, "bot": 1700, "sup": 400}),
    ]
    kill_table = {
        (8, "top"): 0,
        (8, "jng"): 1,
        (8, "mid"): 1,
        (8, "bot"): 0,
        (8, "sup"): 0,
        (14, "top"): 1,
        (14, "jng"): 2,
        (14, "mid"): 3,
        (14, "bot"): 2,
        (14, "sup"): 1,
        (20, "top"): 2,
        (20, "jng"): 3,
        (20, "mid"): 5,
        (20, "bot"): 4,
        (20, "sup"): 2,
        (25, "top"): 3,
        (25, "jng"): 4,
        (25, "mid"): 6,
        (25, "bot"): 5,
        (25, "sup"): 3,
    }
    for minute, diffs in checkpoints:
        for lane, gold_diff in diffs.items():
            lane_states.append(
                LaneState(
                    at_min=minute,
                    lane=lane,
                    gold_diff=sign * gold_diff,
                    cs_diff=sign * (gold_diff // 20),
                    xp_diff=sign * (gold_diff // 2),
                    kills=kill_table[(minute, lane)],
                )
            )

    # Smooth gold curve over 28 minutes; analyzed side pulls ahead after 10.
    team_gold_diff_by_min = [sign * int(120 * m - 200) if m > 2 else 0 for m in range(29)]

    objectives = [
        Objective(
            t=8 * 60 + 15,
            type="dragon",
            subtype="infernal",
            team=side,
            gold_diff_at_event=sign * 300,
            tradeoff="",
        ),
        Objective(
            t=9 * 60 + 30,
            type="herald",
            subtype="",
            team=side,
            gold_diff_at_event=sign * 500,
            tradeoff="tower_top",
        ),
        Objective(
            t=12 * 60 + 5,
            type="tower",
            subtype="outer",
            team=side,
            gold_diff_at_event=sign * 800,
            tradeoff="dragon" if result == "win" else "",
        ),
        Objective(
            t=15 * 60 + 40,
            type="dragon",
            subtype="cloud",
            team="red" if side == "blue" else "blue",
            gold_diff_at_event=sign * 900,
            tradeoff="",
        ),
        Objective(
            t=22 * 60 + 10,
            type="baron",
            subtype="",
            team=side,
            gold_diff_at_event=sign * 1800,
            tradeoff="",
        ),
        Objective(
            t=26 * 60 + 0,
            type="inhibitor",
            subtype="",
            team=side,
            gold_diff_at_event=sign * 4200,
            tradeoff="",
        ),
    ]

    fights = [
        Fight(
            t=9 * 60 + 10,
            where="river_top",
            kills_for=2,
            kills_against=1,
            gold_swing=sign * 600,
            led_to="herald",
            players_near=["Vi", "Syndra", "Lee Sin", "Zed"],
        ),
        Fight(
            t=15 * 60 + 30,
            where="dragon_pit",
            kills_for=1,
            kills_against=3,
            gold_swing=-sign * 900,
            led_to="dragon",
            players_near=["Jinx", "Thresh", "Caitlyn", "Lux", "Lee Sin"],
        ),
        Fight(
            t=21 * 60 + 50,
            where="baron_pit",
            kills_for=4,
            kills_against=1,
            gold_swing=sign * 2400,
            led_to="baron",
            players_near=["Vi", "Syndra", "Jinx", "Thresh", "Lee Sin", "Zed"],
        ),
        Fight(
            t=27 * 60 + 20,
            where="mid_lane",
            kills_for=4,
            kills_against=0,
            gold_swing=sign * 3000,
            led_to="inhibitor",
            players_near=["Darius", "Vi", "Syndra", "Jinx", "Thresh"],
        ),
    ]

    jungle_path = JunglePath(
        blue=[
            "blue_buff",
            "gromp",
            "wolves",
            "red_buff",
            "raptors",
            "krugs",
            "scuttle_bot",
            "blue_buff",
            "gromp",
        ],
        red=[
            "red_buff",
            "krugs",
            "raptors",
            "blue_buff",
            "wolves",
            "gromp",
            "scuttle_top",
            "red_buff",
            "krugs",
        ],
    )

    analyzed_carries = ["Syndra", "Jinx"] if side == "blue" else ["Zed", "Caitlyn"]
    recalls = [
        Recall(player=analyzed_carries[0], t=6 * 60 + 5, synced_with_team=True),
        Recall(player=analyzed_carries[1], t=7 * 60 + 50, synced_with_team=False),
        Recall(player=analyzed_carries[0], t=13 * 60 + 20, synced_with_team=True),
    ]

    return GameDigest(
        meta=meta,
        draft=draft,
        lane_states=lane_states,
        team_gold_diff_by_min=team_gold_diff_by_min,
        objectives=objectives,
        fights=fights,
        jungle_path=jungle_path,
        recalls=recalls,
    )


def _run(args: argparse.Namespace) -> int:
    db = init_db()
    try:
        digest = _build_fake_digest(args.game_id, args.side, args.result)
        save_game(db, digest)
        logger.info(
            "Saved fake game %s | patch=%s | side=%s | result=%s | fights=%d | objectives=%d",
            digest.meta.game_id,
            digest.meta.patch,
            digest.meta.side,
            digest.meta.result,
            len(digest.fights),
            len(digest.objectives),
        )
        return 0
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Insert a synthetic GameDigest into DuckDB.")
    parser.add_argument(
        "--game-id",
        default="EUW1_FAKE001",
        help="Game ID — must match Riot match-v5 pattern (default: EUW1_FAKE001)",
    )
    parser.add_argument(
        "--side", choices=["blue", "red"], default="blue", help="Analyzed side (default: blue)"
    )
    parser.add_argument(
        "--result",
        choices=["win", "loss"],
        default="win",
        help="Result for the analyzed side (default: win)",
    )
    args = parser.parse_args()
    sys.exit(_run(args))


if __name__ == "__main__":
    main()
