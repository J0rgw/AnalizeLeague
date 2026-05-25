// Types mirror backend/app/digest/models.py exactly.
// Field names match /.ai/digest-schema.md. Do not add or rename fields.

export type Side = "blue" | "red";
export type Result = "win" | "loss";
export type Lane = "top" | "jng" | "mid" | "bot" | "sup";
export type ObjectiveType =
  | "baron"
  | "dragon"
  | "herald"
  | "tower"
  | "inhibitor";

export interface GameMeta {
  game_id: string;
  patch: string;
  duration_s: number;
  side: Side;
  result: Result;
}

export interface DraftSide {
  top: string;
  jng: string;
  mid: string;
  bot: string;
  sup: string;
}

export interface DraftBans {
  blue: [string, string, string, string, string];
  red: [string, string, string, string, string];
}

export interface Draft {
  blue: DraftSide;
  red: DraftSide;
  bans: DraftBans;
}

export interface LaneState {
  at_min: number;
  lane: Lane;
  gold_diff: number;
  cs_diff: number;
  xp_diff: number;
  kills: number;
}

export interface Objective {
  t: number;
  type: ObjectiveType;
  subtype: string;
  team: Side;
  gold_diff_at_event: number;
  tradeoff: string;
}

export interface Fight {
  t: number;
  where: string;
  kills_for: number;
  kills_against: number;
  gold_swing: number;
  led_to: string;
  players_near: string[];
}

export interface JunglePath {
  blue: string[];
  red: string[];
}

export interface Recall {
  player: string;
  t: number;
  synced_with_team: boolean;
}

export interface GameDigest {
  meta: GameMeta;
  draft: Draft;
  lane_states: LaneState[];
  team_gold_diff_by_min: number[];
  objectives: Objective[];
  fights: Fight[];
  jungle_path: JunglePath;
  recalls: Recall[];
}
