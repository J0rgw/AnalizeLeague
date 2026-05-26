# Game Digest Schema — Canonical Contract

The GameDigest is the shared contract between:
- **Backend digest builder**: `backend/app/digest/builder.py` (produces it)
- **LLM prompting layer**: `backend/app/llm/agent.py` (consumes it)
- **Frontend display layer**: Phase 2 (renders it)

Pydantic models in `backend/app/digest/models.py` enforce this schema at runtime.
All field names in code match this document exactly.

## Conventions

- **Gold/CS/XP diffs**: positive = the analyzed team (`meta.side`) is ahead.
- **Timestamps** (`t`): seconds from game start.
- **`lane_states`**: snapshots taken at minutes **8, 14, 20** (laning, mid-game, mid-late). Match `_LANE_CHECKPOINTS` in `backend/app/digest/builder.py`.
- **`fights`**: only engagements with ≥ 1 kill, clustered within `_FIGHT_WINDOW_MS` (15 s).
- **`jungle_path`**: ordered camp labels from the first ~4 minutes, reconstructed **approximately** from `jungleMinionsKilled` deltas + jungler position (Riot timelines do not emit per-camp events). See `/.ai/data-sources.md`.
- **`bans`**: champion **names** resolved via the cached Data Dragon CDN. If both network and cache fail the resolver degrades to `str(championId)`, preserving the `list[str]` schema.

## Full annotated schema

```json
{
  "meta": {
    "game_id":    "string  — unique identifier from the data source",
    "patch":      "string  — e.g. '14.10'",
    "duration_s": "int     — game duration in seconds",
    "side":       "string  — 'blue' | 'red'  (the team being analyzed)",
    "result":     "string  — 'win' | 'loss'"
  },

  "draft": {
    "blue": {
      "top": "string — champion name",
      "jng": "string",
      "mid": "string",
      "bot": "string",
      "sup": "string"
    },
    "red": {
      "top": "string",
      "jng": "string",
      "mid": "string",
      "bot": "string",
      "sup": "string"
    },
    "bans": {
      "blue": ["string", "string", "string", "string", "string"],
      "red":  ["string", "string", "string", "string", "string"]
    }
  },

  "lane_states": [
    {
      "at_min":    "int    — minute mark (8 | 14 | 20)",
      "lane":      "string — 'top' | 'jng' | 'mid' | 'bot' | 'sup'",
      "gold_diff": "int    — positive = analyzed team ahead",
      "cs_diff":   "int    — positive = analyzed team ahead",
      "xp_diff":   "int    — positive = analyzed team ahead",
      "kills":     "int    — cumulative kills by the analyzed team's player in this lane up to the snapshot"
    }
  ],

  "team_gold_diff_by_min": [
    "int — index = minute, value = team total gold diff (positive = analyzed team ahead)"
  ],

  "objectives": [
    {
      "t":                  "int    — timestamp in seconds",
      "type":               "string — 'baron' | 'dragon' | 'herald' | 'tower' | 'inhibitor' | 'void_grubs'",
      "subtype":            "string — dragon element (e.g. 'infernal'), tower descriptor (e.g. 'mid_outer'), inhibitor lane, '' otherwise",
      "team":               "string — 'blue' | 'red' (team that secured the objective)",
      "gold_diff_at_event": "int    — team gold diff at the moment of the objective",
      "tradeoff":           "string — what the other team did simultaneously, or ''"
    }
  ],

  "fights": [
    {
      "t":             "int    — timestamp in seconds (first kill in the fight)",
      "where":         "string — map zone label, e.g. 'river_top', 'baron_pit', 'mid_lane'",
      "kills_for":     "int    — kills by the analyzed team",
      "kills_against": "int    — kills by the opponent",
      "gold_swing":    "int    — gold advantage gained (+) or lost (-) by the fight",
      "led_to":        "string — subsequent objective, e.g. 'baron', 'tower_top', ''",
      "players_near":  ["string — player identifiers near the fight location"]
    }
  ],

  "jungle_path": {
    "blue": ["string — ordered camp label, e.g. 'red_buff', 'raptors', 'gromp'"],
    "red":  ["string"]
  },

  "recalls": [
    {
      "player":           "string — player identifier",
      "t":                "int    — timestamp in seconds",
      "synced_with_team": "bool   — true if the recall timing aligns with ≥ 2 teammates"
    }
  ]
}
```

## Pydantic models reference

| Model | Fields |
|-------|--------|
| `GameMeta` | `game_id`, `patch`, `duration_s`, `side`, `result` |
| `DraftSide` | `top`, `jng`, `mid`, `bot`, `sup` |
| `DraftBans` | `blue: list[str]`, `red: list[str]` |
| `Draft` | `blue: DraftSide`, `red: DraftSide`, `bans: DraftBans` |
| `LaneState` | `at_min`, `lane`, `gold_diff`, `cs_diff`, `xp_diff`, `kills` |
| `Objective` | `t`, `type`, `subtype`, `team`, `gold_diff_at_event`, `tradeoff` |
| `Fight` | `t`, `where`, `kills_for`, `kills_against`, `gold_swing`, `led_to`, `players_near` |
| `JunglePath` | `blue: list[str]`, `red: list[str]` |
| `Recall` | `player`, `t`, `synced_with_team` |
| `GameDigest` | all of the above composed |
