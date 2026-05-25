"""
Pydantic models for the GameDigest — the canonical compact representation
of a single League of Legends game.

This is the shared contract between:
  - backend/app/digest/builder.py  (produces GameDigest)
  - backend/app/llm/agent.py       (consumes GameDigest for prompting)
  - frontend (Phase 2)             (displays GameDigest fields)

Full schema documentation: /.ai/digest-schema.md
All field names match the digest-schema.md contract exactly.
Convention: gold/cs/xp diffs are positive when the analyzed team (meta.side) is ahead.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class GameMeta(BaseModel):
    game_id: str
    patch: str
    duration_s: int
    side: str   # "blue" | "red" — the team being analyzed
    result: str  # "win" | "loss"


class DraftSide(BaseModel):
    top: str
    jng: str
    mid: str
    bot: str
    sup: str


class DraftBans(BaseModel):
    blue: list[str]
    red: list[str]


class Draft(BaseModel):
    blue: DraftSide
    red: DraftSide
    bans: DraftBans


class LaneState(BaseModel):
    at_min: int
    lane: str        # "top" | "jng" | "mid" | "bot" | "sup"
    gold_diff: int
    cs_diff: int
    xp_diff: int
    kills: int


class Objective(BaseModel):
    t: int            # timestamp in seconds
    type: str         # "baron" | "dragon" | "herald" | "tower" | "inhibitor"
    subtype: str      # e.g. "infernal", "outer", "" for none
    team: str         # "blue" | "red"
    gold_diff_at_event: int
    tradeoff: str     # what the other team did simultaneously, or ""


class Fight(BaseModel):
    t: int
    where: str        # map zone label, e.g. "river_top", "baron_pit"
    kills_for: int
    kills_against: int
    gold_swing: int   # positive = analyzed team gained
    led_to: str       # subsequent objective, e.g. "baron", "tower_top", ""
    players_near: list[str]


class JunglePath(BaseModel):
    blue: list[str]   # ordered camp label strings, e.g. ["red_buff", "raptors", ...]
    red: list[str]


class Recall(BaseModel):
    player: str
    t: int
    synced_with_team: bool


class GameDigest(BaseModel):
    """Canonical compact representation of a single League of Legends game."""

    meta: GameMeta
    draft: Draft
    lane_states: list[LaneState] = Field(default_factory=list)
    team_gold_diff_by_min: list[int] = Field(default_factory=list)
    objectives: list[Objective] = Field(default_factory=list)
    fights: list[Fight] = Field(default_factory=list)
    jungle_path: JunglePath
    recalls: list[Recall] = Field(default_factory=list)
