"""
Digest builder: converts raw Riot API game data into a compact GameDigest.

Design: ALL heavy computation happens here in Python/Polars.
The LLM receives only the finished ~2 KB GameDigest, never raw API payloads.

Input shape (from RiotDataSource.get_game):
    {
        "game_id":  str,
        "match":    dict  # Riot match-v5 response
        "timeline": dict  # Riot timeline-v5 response
    }
"""

from __future__ import annotations

import logging
from typing import Any

import polars as pl

from app.digest.champions import resolve_champion_name
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

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

_BLUE_TEAM = 100
_RED_TEAM = 200

_LANE_CHECKPOINTS: tuple[int, ...] = (8, 14, 20)  # minutes

_FIGHT_WINDOW_MS = 15_000  # kills within 15 s are the same fight
_TRADEOFF_WINDOW_MS = 30_000  # ±30 s for concurrent tradeoff detection
_LED_TO_WINDOW_MS = 60_000  # objective taken within 60 s after fight end

_BLUE_SPAWN = (500, 500)
_RED_SPAWN = (14_300, 14_300)
_RECALL_DIST = 1_500  # units from spawn to infer a recall

_POS_TO_LANE: dict[str, str] = {
    "TOP": "top",
    "JUNGLE": "jng",
    "MIDDLE": "mid",
    "BOTTOM": "bot",
    "UTILITY": "sup",
}

# Approximate camp centres in Riot's coordinate space (0..14820). Used to
# infer which camp a jungler just cleared based on their position when
# jungleMinionsKilled increments — Riot timeline frames are 1-minute snapshots
# and don't emit per-camp events, so this is necessarily fuzzy. GRID Series
# Events provide exact per-clear timestamps; see /.ai/data-sources.md.
_JUNGLE_CAMP_CENTERS: tuple[tuple[str, int, int], ...] = (
    # Blue-side jungle
    ("gromp", 2_150, 8_400),
    ("blue_buff", 3_850, 7_950),
    ("wolves", 3_900, 6_500),
    ("raptors", 6_900, 5_500),
    ("red_buff", 7_850, 4_100),
    ("krugs", 8_350, 2_500),
    # Red-side jungle (same camp types, mirrored)
    ("krugs", 6_550, 12_300),
    ("red_buff", 7_050, 10_500),
    ("raptors", 7_900, 9_500),
    ("wolves", 10_800, 8_350),
    ("blue_buff", 10_950, 6_850),
    ("gromp", 12_750, 6_400),
    # Scuttle crabs (river)
    ("scuttle_crab", 4_600, 10_100),
    ("scuttle_crab", 10_500, 4_500),
)

_EPIC_LABELS: dict[str, str] = {
    "BARON_NASHOR": "baron",
    "RIFTHERALD": "herald",
    "HORDE": "void_grubs",
}

_DRAGON_SUBTYPES: dict[str, str] = {
    "FIRE_DRAGON": "infernal",
    "EARTH_DRAGON": "mountain",
    "WATER_DRAGON": "ocean",
    "AIR_DRAGON": "cloud",
    "HEXTECH_DRAGON": "hextech",
    "CHEMTECH_DRAGON": "chemtech",
    "ELDER_DRAGON": "elder",
}

_TOWER_SUBTYPES: dict[str, str] = {
    "OUTER_TURRET": "outer",
    "INNER_TURRET": "inner",
    "BASE_TURRET": "base",
    "NEXUS_TURRET": "nexus",
}


# ── Map helpers ───────────────────────────────────────────────────────────────


def _position_to_zone(x: int, y: int) -> str:
    """Map Riot coordinate space (0–14820) to a named map zone."""
    # Check specific lane extremes first (base/inhibitor areas)
    if x < 3_500 and y > 11_000:
        return "top_lane"
    if x > 11_000 and y < 3_500:
        return "bot_lane"
    # River / pit areas
    if x < 5_800 and y > 9_600:
        return "baron_pit" if (4_000 < x < 5_800 and 9_600 < y < 11_200) else "river_top"
    if x > 9_000 and y < 5_200:
        return "dragon_pit" if (9_000 < x < 11_000 and 3_500 < y < 5_200) else "river_bot"
    if 5_000 <= x <= 9_500 and 5_000 <= y <= 9_500:
        return "mid_lane"
    if x < 7_500:
        return "blue_jungle"
    return "red_jungle"


# ── Frame DataFrame ───────────────────────────────────────────────────────────


def _build_frames_df(
    participants: list[dict[str, Any]],
    frames: list[dict[str, Any]],
) -> pl.DataFrame:
    """Flatten timeline participant frames into a Polars DataFrame."""
    pid_to_team = {p["participantId"]: p["teamId"] for p in participants}
    pid_to_lane = {
        p["participantId"]: _POS_TO_LANE.get(p.get("teamPosition", ""), "") for p in participants
    }

    rows: list[dict[str, Any]] = []
    for frame in frames:
        t_ms = int(frame["timestamp"])
        for pid_str, pf in frame.get("participantFrames", {}).items():
            pid = int(pid_str)
            pos = pf.get("position", {})
            rows.append(
                {
                    "t_ms": t_ms,
                    "pid": pid,
                    "team_id": pid_to_team.get(pid, 0),
                    "lane": pid_to_lane.get(pid, ""),
                    "total_gold": int(pf.get("totalGold", 0)),
                    "cs": int(pf.get("minionsKilled", 0)) + int(pf.get("jungleMinionsKilled", 0)),
                    "xp": int(pf.get("xp", 0)),
                    "x": int(pos.get("x", 0)),
                    "y": int(pos.get("y", 0)),
                }
            )

    if not rows:
        return pl.DataFrame(
            schema={
                "t_ms": pl.Int64,
                "pid": pl.Int32,
                "team_id": pl.Int32,
                "lane": pl.String,
                "total_gold": pl.Int64,
                "cs": pl.Int32,
                "xp": pl.Int64,
                "x": pl.Int32,
                "y": pl.Int32,
            }
        )
    return pl.DataFrame(rows)


# ── Gold helpers ──────────────────────────────────────────────────────────────


def _team_gold_at(df: pl.DataFrame, t_ms: int, team_id: int) -> int:
    available = df.filter(pl.col("t_ms") <= t_ms).select(pl.col("t_ms").max()).item()
    if available is None:
        return 0
    return int(
        df.filter((pl.col("t_ms") == available) & (pl.col("team_id") == team_id))[
            "total_gold"
        ].sum()
    )


def _gold_diff_at(df: pl.DataFrame, t_ms: int, analyzed_team_id: int) -> int:
    opp = _RED_TEAM if analyzed_team_id == _BLUE_TEAM else _BLUE_TEAM
    return _team_gold_at(df, t_ms, analyzed_team_id) - _team_gold_at(df, t_ms, opp)


# ── Sub-builders ──────────────────────────────────────────────────────────────


def _build_meta(raw: dict[str, Any], analyzed_team_id: int) -> GameMeta:
    info: dict[str, Any] = raw["match"]["info"]
    version: str = info.get("gameVersion", "0.0")
    patch = ".".join(version.split(".")[:2])
    duration_s = int(info.get("gameDuration", 0))
    side = "blue" if analyzed_team_id == _BLUE_TEAM else "red"
    result = "loss"
    for team in info.get("teams", []):
        if team["teamId"] == analyzed_team_id and team.get("win"):
            result = "win"
            break
    return GameMeta(
        game_id=raw["game_id"],
        patch=patch,
        duration_s=duration_s,
        side=side,
        result=result,
    )


def _build_draft(match_info: dict[str, Any], patch: str | None = None) -> Draft:
    blue: dict[str, str] = {}
    red: dict[str, str] = {}
    for p in match_info.get("participants", []):
        pos = _POS_TO_LANE.get(p.get("teamPosition", ""), "")
        if not pos:
            continue
        champ = p.get("championName", "Unknown")
        (blue if p["teamId"] == _BLUE_TEAM else red)[pos] = champ

    def _side(d: dict[str, str]) -> DraftSide:
        return DraftSide(
            top=d.get("top", "Unknown"),
            jng=d.get("jng", "Unknown"),
            mid=d.get("mid", "Unknown"),
            bot=d.get("bot", "Unknown"),
            sup=d.get("sup", "Unknown"),
        )

    blue_bans: list[str] = []
    red_bans: list[str] = []
    for team in match_info.get("teams", []):
        # Resolve numeric championIds to display names via Data Dragon. The
        # resolver degrades to str(id) if both network and cache fail, so
        # the schema (list[str]) is never violated.
        bans = [resolve_champion_name(b.get("championId", ""), patch) for b in team.get("bans", [])]
        while len(bans) < 5:
            bans.append("")
        if team["teamId"] == _BLUE_TEAM:
            blue_bans = bans[:5]
        else:
            red_bans = bans[:5]

    return Draft(
        blue=_side(blue),
        red=_side(red),
        bans=DraftBans(blue=blue_bans, red=red_bans),
    )


def _build_lane_states(
    df: pl.DataFrame,
    all_events: list[dict[str, Any]],
    analyzed_team_id: int,
    pid_to_team: dict[int, int],
    pid_to_lane: dict[int, str],
) -> list[LaneState]:
    opp = _RED_TEAM if analyzed_team_id == _BLUE_TEAM else _BLUE_TEAM

    # Pre-aggregate kills per (checkpoint_min, lane)
    kill_counts: dict[tuple[int, str], int] = {}
    for checkpoint_min in _LANE_CHECKPOINTS:
        cut = checkpoint_min * 60_000
        for e in all_events:
            if int(e.get("timestamp", 0)) > cut:
                break
            if e.get("type") != "CHAMPION_KILL":
                continue
            killer = int(e.get("killerId", 0))
            if pid_to_team.get(killer) == analyzed_team_id:
                lane = pid_to_lane.get(killer, "")
                if lane:
                    kill_counts[(checkpoint_min, lane)] = (
                        kill_counts.get((checkpoint_min, lane), 0) + 1
                    )

    states: list[LaneState] = []
    for checkpoint_min in _LANE_CHECKPOINTS:
        target_ms = checkpoint_min * 60_000
        available = df.filter(pl.col("t_ms") <= target_ms).select(pl.col("t_ms").max()).item()
        if available is None:
            continue
        frame = df.filter(pl.col("t_ms") == available)

        for lane in ("top", "jng", "mid", "bot", "sup"):
            a_rows = frame.filter(
                (pl.col("team_id") == analyzed_team_id) & (pl.col("lane") == lane)
            )
            o_rows = frame.filter((pl.col("team_id") == opp) & (pl.col("lane") == lane))
            if a_rows.is_empty() or o_rows.is_empty():
                gold_diff = cs_diff = xp_diff = 0
            else:
                gold_diff = int(a_rows["total_gold"][0]) - int(o_rows["total_gold"][0])
                cs_diff = int(a_rows["cs"][0]) - int(o_rows["cs"][0])
                xp_diff = int(a_rows["xp"][0]) - int(o_rows["xp"][0])

            states.append(
                LaneState(
                    at_min=checkpoint_min,
                    lane=lane,
                    gold_diff=gold_diff,
                    cs_diff=cs_diff,
                    xp_diff=xp_diff,
                    kills=kill_counts.get((checkpoint_min, lane), 0),
                )
            )
    return states


def _build_team_gold_diff_by_min(df: pl.DataFrame, analyzed_team_id: int) -> list[int]:
    opp = _RED_TEAM if analyzed_team_id == _BLUE_TEAM else _BLUE_TEAM
    # Polars typing for .max() is a wide union; narrow to int explicitly.
    raw_max = df["t_ms"].max()
    max_ms = int(raw_max) if isinstance(raw_max, (int, float)) else 0
    max_min = max_ms // 60_000
    result: list[int] = []
    for minute in range(max_min + 1):
        t_ms = minute * 60_000
        available = df.filter(pl.col("t_ms") <= t_ms).select(pl.col("t_ms").max()).item()
        if available is None:
            result.append(result[-1] if result else 0)
            continue
        frame = df.filter(pl.col("t_ms") == available)
        a_g = int(frame.filter(pl.col("team_id") == analyzed_team_id)["total_gold"].sum())
        o_g = int(frame.filter(pl.col("team_id") == opp)["total_gold"].sum())
        result.append(a_g - o_g)
    return result


def _find_tradeoff(
    all_events: list[dict[str, Any]],
    skip_idx: int,
    t_ms: int,
    killer_team_id: int,
) -> str:
    """Return a description of what the opponent did concurrently, or ''."""
    opp = _RED_TEAM if killer_team_id == _BLUE_TEAM else _BLUE_TEAM
    lo, hi = t_ms - _TRADEOFF_WINDOW_MS, t_ms + _TRADEOFF_WINDOW_MS
    for j, e2 in enumerate(all_events):
        if j == skip_idx:
            continue
        et2 = int(e2.get("timestamp", 0))
        if et2 < lo:
            continue
        if et2 > hi:
            break
        etype2 = e2.get("type", "")
        if etype2 == "ELITE_MONSTER_KILL" and int(e2.get("killerTeamId", 0)) == opp:
            m = e2.get("monsterType", "")
            label = _EPIC_LABELS.get(m, m.lower())
            return f"Opponent secured {label}"
        if etype2 == "BUILDING_KILL":
            # teamId = team that LOST the building
            destroyed_team = int(e2.get("teamId", 0))
            if destroyed_team == killer_team_id:
                btype = e2.get("buildingType", "")
                return "Tower traded away" if "TOWER" in btype else "Structure traded away"
    return ""


def _build_objectives(
    all_events: list[dict[str, Any]],
    analyzed_team_id: int,
    df: pl.DataFrame,
) -> list[Objective]:
    objs: list[Objective] = []
    for i, e in enumerate(all_events):
        etype = e.get("type", "")
        t_ms = int(e.get("timestamp", 0))
        t_s = t_ms // 1000

        if etype == "ELITE_MONSTER_KILL":
            monster = e.get("monsterType", "")
            killer_team = int(e.get("killerTeamId", 0))
            team_side = "blue" if killer_team == _BLUE_TEAM else "red"

            if monster == "DRAGON":
                subtype_raw = e.get("monsterSubType", "")
                subtype = _DRAGON_SUBTYPES.get(subtype_raw, "dragon")
                obj_type = "dragon"
            elif monster in _EPIC_LABELS:
                obj_type = _EPIC_LABELS[monster]
                subtype = ""
            else:
                continue

            gold_diff = _gold_diff_at(df, t_ms, analyzed_team_id)
            tradeoff = _find_tradeoff(all_events, i, t_ms, killer_team)
            objs.append(
                Objective(
                    t=t_s,
                    type=obj_type,
                    subtype=subtype,
                    team=team_side,
                    gold_diff_at_event=gold_diff,
                    tradeoff=tradeoff,
                )
            )

        elif etype == "BUILDING_KILL":
            btype = e.get("buildingType", "")
            # teamId = team that lost the building; killer = the other team
            lost_team = int(e.get("teamId", 0))
            killer_team = _RED_TEAM if lost_team == _BLUE_TEAM else _BLUE_TEAM
            team_side = "blue" if killer_team == _BLUE_TEAM else "red"

            if btype == "TOWER_BUILDING":
                obj_type = "tower"
                tower_t = _TOWER_SUBTYPES.get(e.get("towerType", ""), "")
                lane_raw = e.get("laneType", "").lower().replace("_lane", "")
                subtype = f"{lane_raw}_{tower_t}" if tower_t and lane_raw else lane_raw or tower_t
            elif btype == "INHIBITOR_BUILDING":
                obj_type = "inhibitor"
                subtype = e.get("laneType", "").lower().replace("_lane", "")
            else:
                continue

            gold_diff = _gold_diff_at(df, t_ms, analyzed_team_id)
            tradeoff = _find_tradeoff(all_events, i, t_ms, killer_team)
            objs.append(
                Objective(
                    t=t_s,
                    type=obj_type,
                    subtype=subtype,
                    team=team_side,
                    gold_diff_at_event=gold_diff,
                    tradeoff=tradeoff,
                )
            )

    return objs


def _build_fights(
    all_events: list[dict[str, Any]],
    analyzed_team_id: int,
    pid_to_team: dict[int, int],
    pid_to_champ: dict[int, str],
    df: pl.DataFrame,
    objectives: list[Objective],
) -> list[Fight]:
    kill_events = [e for e in all_events if e.get("type") == "CHAMPION_KILL"]
    if not kill_events:
        return []

    # Cluster consecutive kills within _FIGHT_WINDOW_MS of each other
    clusters: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for e in kill_events:
        if not current:
            current = [e]
        elif int(e["timestamp"]) - int(current[-1]["timestamp"]) <= _FIGHT_WINDOW_MS:
            current.append(e)
        else:
            clusters.append(current)
            current = [e]
    if current:
        clusters.append(current)

    opp = _RED_TEAM if analyzed_team_id == _BLUE_TEAM else _BLUE_TEAM
    fights: list[Fight] = []

    for cluster in clusters:
        t_ms = int(cluster[0]["timestamp"])
        t_s = t_ms // 1000
        last_ms = int(cluster[-1]["timestamp"])

        pos = cluster[0].get("position", {})
        zone = _position_to_zone(int(pos.get("x", 7000)), int(pos.get("y", 7000)))

        kills_for = sum(
            1 for e in cluster if pid_to_team.get(int(e.get("killerId", 0))) == analyzed_team_id
        )
        kills_against = sum(1 for e in cluster if pid_to_team.get(int(e.get("killerId", 0))) == opp)

        # Gold swing: compare team gold diff before vs ~1 min after fight
        gold_before = _gold_diff_at(df, max(0, t_ms - 1), analyzed_team_id)
        gold_after = _gold_diff_at(df, last_ms + 60_000, analyzed_team_id)
        gold_swing = gold_after - gold_before

        # First objective taken within 60 s of the fight ending
        led_to = ""
        for obj in objectives:
            obj_ms = obj.t * 1000
            if last_ms < obj_ms <= last_ms + _LED_TO_WINDOW_MS:
                led_to = f"{obj.type}_{obj.subtype}" if obj.subtype else obj.type
                break

        involved: set[int] = set()
        for e in cluster:
            for field in ("killerId", "victimId"):
                pid = int(e.get(field, 0))
                if pid:
                    involved.add(pid)
            for a in e.get("assistingParticipantIds", []):
                involved.add(int(a))
        players_near = [pid_to_champ.get(pid, str(pid)) for pid in sorted(involved)]

        fights.append(
            Fight(
                t=t_s,
                where=zone,
                kills_for=kills_for,
                kills_against=kills_against,
                gold_swing=gold_swing,
                led_to=led_to,
                players_near=players_near,
            )
        )

    return fights


def _nearest_camp_label(x: int, y: int) -> str:
    """Return the closest known jungle-camp label to (x, y)."""
    best_label = ""
    best_d2 = float("inf")
    for label, cx, cy in _JUNGLE_CAMP_CENTERS:
        d2 = (x - cx) ** 2 + (y - cy) ** 2
        if d2 < best_d2:
            best_d2 = d2
            best_label = label
    return best_label


def _build_jungle_path(
    frames: list[dict[str, Any]],
    all_events: list[dict[str, Any]],
    pid_to_team: dict[int, int],
    pid_to_lane: dict[int, str],
) -> JunglePath:
    """
    Reconstruct the early jungle clear path (first ~4 minutes), APPROXIMATELY.

    Riot timeline frames are 1-minute snapshots and do NOT emit a per-camp
    event (only ELITE_MONSTER_KILL for dragon/herald/baron/grubs exists).
    We therefore infer camps by:
      1. Watching each jungler's `jungleMinionsKilled` counter for increments
         between frames — a positive delta means at least one camp was cleared
         in that minute.
      2. Labelling the increment with the camp closest to the jungler's
         position at the end of that frame.
      3. Appending real epic monsters from ELITE_MONSTER_KILL events on top.

    Limitations of this approximation: a jungler clearing two adjacent camps
    in one minute only contributes one label, and a jungler standing between
    two camps may be misattributed. GRID Series Events provide exact
    sub-second clear timestamps and resolve both issues; see
    /.ai/data-sources.md for the data-source comparison.
    """
    blue: list[str] = []
    red: list[str] = []
    cutoff_ms = 4 * 60_000

    junglers = [pid for pid, lane in pid_to_lane.items() if lane == "jng"]
    prev_jm: dict[int, int] = {pid: 0 for pid in junglers}

    for frame in frames:
        t_ms = int(frame.get("timestamp", 0))
        if t_ms > cutoff_ms:
            break
        pframes: dict[str, Any] = frame.get("participantFrames", {})
        for pid in junglers:
            pf = pframes.get(str(pid))
            if not pf:
                continue
            jm = int(pf.get("jungleMinionsKilled", 0))
            delta = jm - prev_jm[pid]
            prev_jm[pid] = jm
            if delta <= 0 or t_ms == 0:
                continue
            pos = pf.get("position", {})
            x, y = int(pos.get("x", 0)), int(pos.get("y", 0))
            label = _nearest_camp_label(x, y)
            if not label:
                continue
            team = pid_to_team.get(pid, 0)
            if team == _BLUE_TEAM:
                blue.append(label)
            elif team == _RED_TEAM:
                red.append(label)

    # Real epic monsters within the cutoff (these DO emit timeline events).
    for e in all_events:
        if int(e.get("timestamp", 0)) > cutoff_ms:
            break
        if e.get("type") != "ELITE_MONSTER_KILL":
            continue
        killer = int(e.get("killerId", 0))
        if pid_to_lane.get(killer) != "jng":
            continue
        monster = e.get("monsterType", "")
        if monster == "DRAGON":
            label = "dragon"
        elif monster in _EPIC_LABELS:
            label = _EPIC_LABELS[monster]
        else:
            continue
        team = pid_to_team.get(killer, 0)
        if team == _BLUE_TEAM:
            blue.append(label)
        elif team == _RED_TEAM:
            red.append(label)

    return JunglePath(blue=blue, red=red)


def _build_recalls(
    frames: list[dict[str, Any]],
    pid_to_team: dict[int, int],
    pid_to_champ: dict[int, str],
) -> list[Recall]:
    """Infer recalls from a player's position jumping to spawn between frames."""
    recalls: list[Recall] = []
    prev: dict[int, tuple[int, int]] = {}

    for frame in frames:
        t_s = int(frame["timestamp"]) // 1000
        frame_recalls: list[int] = []

        for pid_str, pf in frame.get("participantFrames", {}).items():
            pid = int(pid_str)
            pos = pf.get("position", {})
            x, y = int(pos.get("x", 0)), int(pos.get("y", 0))
            spawn = _BLUE_SPAWN if pid_to_team.get(pid, 0) == _BLUE_TEAM else _RED_SPAWN

            dist = ((x - spawn[0]) ** 2 + (y - spawn[1]) ** 2) ** 0.5
            prev_pos = prev.get(pid)
            if prev_pos is not None:
                prev_dist = ((prev_pos[0] - spawn[0]) ** 2 + (prev_pos[1] - spawn[1]) ** 2) ** 0.5
                if prev_dist > 3_000 and dist < _RECALL_DIST:
                    frame_recalls.append(pid)
            prev[pid] = (x, y)

        if frame_recalls:
            synced = len(frame_recalls) >= 3
            for pid in frame_recalls:
                recalls.append(
                    Recall(
                        player=pid_to_champ.get(pid, str(pid)),
                        t=t_s,
                        synced_with_team=synced,
                    )
                )

    return recalls


# ── Public entry point ────────────────────────────────────────────────────────


def build_digest(
    raw_game_data: dict[str, Any],
    *,
    analyzed_side: str = "blue",
) -> GameDigest:
    """
    Transform raw game data (from RiotDataSource.get_game) into a GameDigest.

    Args:
        raw_game_data:  Dict with keys "game_id", "match", "timeline".
        analyzed_side:  "blue" | "red" — the team to analyze. Defaults to blue.

    Returns:
        Populated GameDigest ready for LLM prompting and DuckDB storage.
    """
    analyzed_team_id = _BLUE_TEAM if analyzed_side == "blue" else _RED_TEAM

    match_info: dict[str, Any] = raw_game_data["match"]["info"]
    timeline_info: dict[str, Any] = raw_game_data["timeline"]["info"]
    participants: list[dict[str, Any]] = match_info.get("participants", [])
    frames: list[dict[str, Any]] = timeline_info.get("frames", [])

    pid_to_team = {p["participantId"]: p["teamId"] for p in participants}
    pid_to_lane = {
        p["participantId"]: _POS_TO_LANE.get(p.get("teamPosition", ""), "") for p in participants
    }
    pid_to_champ = {
        p["participantId"]: p.get("championName", str(p["participantId"])) for p in participants
    }

    all_events: list[dict[str, Any]] = []
    for f in frames:
        all_events.extend(f.get("events", []))

    df = _build_frames_df(participants, frames)

    meta = _build_meta(raw_game_data, analyzed_team_id)
    draft = _build_draft(match_info, patch=meta.patch)
    lane_states = _build_lane_states(df, all_events, analyzed_team_id, pid_to_team, pid_to_lane)
    team_gold_diff = _build_team_gold_diff_by_min(df, analyzed_team_id)
    objectives = _build_objectives(all_events, analyzed_team_id, df)
    fights = _build_fights(all_events, analyzed_team_id, pid_to_team, pid_to_champ, df, objectives)
    jungle_path = _build_jungle_path(frames, all_events, pid_to_team, pid_to_lane)
    recalls = _build_recalls(frames, pid_to_team, pid_to_champ)

    logger.info(
        "Digest built: %s | %d fights | %d objectives | side=%s result=%s",
        meta.game_id,
        len(fights),
        len(objectives),
        meta.side,
        meta.result,
    )

    return GameDigest(
        meta=meta,
        draft=draft,
        lane_states=lane_states,
        team_gold_diff_by_min=team_gold_diff,
        objectives=objectives,
        fights=fights,
        jungle_path=jungle_path,
        recalls=recalls,
    )
