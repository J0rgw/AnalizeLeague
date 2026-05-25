import type { GameDigest } from "@/types/digest";
import type { AgendaItem, GameSummary } from "@/lib/api";

export const victorySummary: GameSummary = {
  game_id: "scrim-2025-w20-g1",
  patch: "14.10",
  duration_s: 1680,
  side: "blue",
  result: "win",
};

export const victoryDigest: GameDigest = {
  meta: {
    game_id: "scrim-2025-w20-g1",
    patch: "14.10",
    duration_s: 1680,
    side: "blue",
    result: "win",
  },
  draft: {
    blue: { top: "Aatrox", jng: "Graves", mid: "Azir", bot: "Jinx", sup: "Nautilus" },
    red:  { top: "Renekton", jng: "Lee Sin", mid: "LeBlanc", bot: "Caitlyn", sup: "Thresh" },
    bans: {
      blue: ["Zeri", "Maokai", "Jayce", "Orianna", "Xin Zhao"],
      red:  ["Yasuo", "Yone", "Kalista", "Akali", "Lucian"],
    },
  },
  lane_states: [
    // Minute 8
    { at_min: 8, lane: "top", gold_diff:  400, cs_diff:  6, xp_diff:  80, kills: 0 },
    { at_min: 8, lane: "jng", gold_diff:  200, cs_diff: 12, xp_diff: 120, kills: 0 },
    { at_min: 8, lane: "mid", gold_diff:  300, cs_diff:  8, xp_diff:  60, kills: 0 },
    { at_min: 8, lane: "bot", gold_diff: -100, cs_diff: -2, xp_diff: -20, kills: 0 },
    { at_min: 8, lane: "sup", gold_diff:  -50, cs_diff:  0, xp_diff:  10, kills: 0 },
    // Minute 14
    { at_min: 14, lane: "top", gold_diff: 1200, cs_diff: 18, xp_diff: 200, kills: 1 },
    { at_min: 14, lane: "jng", gold_diff:  400, cs_diff: 15, xp_diff: 180, kills: 1 },
    { at_min: 14, lane: "mid", gold_diff:  800, cs_diff: 22, xp_diff: 300, kills: 1 },
    { at_min: 14, lane: "bot", gold_diff:  200, cs_diff:  5, xp_diff:  40, kills: 0 },
    { at_min: 14, lane: "sup", gold_diff:  100, cs_diff:  0, xp_diff:  30, kills: 1 },
    // Minute 20
    { at_min: 20, lane: "top", gold_diff: 2100, cs_diff: 30, xp_diff: 400, kills: 2 },
    { at_min: 20, lane: "jng", gold_diff:  800, cs_diff: 20, xp_diff: 250, kills: 2 },
    { at_min: 20, lane: "mid", gold_diff: 1500, cs_diff: 35, xp_diff: 450, kills: 2 },
    { at_min: 20, lane: "bot", gold_diff:  600, cs_diff: 15, xp_diff: 150, kills: 1 },
    { at_min: 20, lane: "sup", gold_diff:  200, cs_diff:  0, xp_diff:  80, kills: 2 },
  ],
  team_gold_diff_by_min: [
    0, 50, 200, 350, 500, 700, 900, 950, 1100,
    1400, 1700, 2000, 2300, 2700, 3200, 3700,
    4200, 4600, 5000, 5200, 5500, 5800, 6100,
    6400, 6700, 7000, 7400, 7900, 8200,
  ],
  objectives: [
    { t: 480,  type: "dragon",    subtype: "infernal", team: "blue", gold_diff_at_event:  800, tradeoff: "" },
    { t: 720,  type: "herald",    subtype: "",          team: "blue", gold_diff_at_event: 1700, tradeoff: "" },
    { t: 960,  type: "dragon",    subtype: "mountain",  team: "blue", gold_diff_at_event: 3200, tradeoff: "" },
    { t: 1200, type: "tower",     subtype: "outer_mid", team: "blue", gold_diff_at_event: 4500, tradeoff: "" },
    { t: 1380, type: "baron",     subtype: "",          team: "blue", gold_diff_at_event: 6100, tradeoff: "" },
    { t: 1500, type: "inhibitor", subtype: "mid",       team: "blue", gold_diff_at_event: 7200, tradeoff: "" },
  ],
  fights: [
    {
      t: 540, where: "river_top",
      kills_for: 2, kills_against: 0, gold_swing: 800,
      led_to: "herald",
      players_near: ["jng", "top", "mid"],
    },
    {
      t: 840, where: "mid_lane",
      kills_for: 3, kills_against: 1, gold_swing: 1200,
      led_to: "tower_mid",
      players_near: ["jng", "mid", "bot", "sup"],
    },
    {
      t: 1320, where: "baron_pit",
      kills_for: 5, kills_against: 0, gold_swing: 3000,
      led_to: "baron",
      players_near: ["top", "jng", "mid", "bot", "sup"],
    },
  ],
  jungle_path: {
    blue: ["red_buff", "raptors", "wolves", "blue_buff", "gromp", "rift_scuttler_top"],
    red:  ["blue_buff", "gromp", "wolves", "red_buff", "raptors", "rift_scuttler_bot"],
  },
  recalls: [
    { player: "blue_top", t:  600, synced_with_team: false },
    { player: "blue_jng", t:  630, synced_with_team: true  },
    { player: "blue_mid", t:  650, synced_with_team: true  },
    { player: "blue_bot", t: 1080, synced_with_team: true  },
    { player: "blue_sup", t: 1080, synced_with_team: true  },
  ],
};

export const victoryAgenda: AgendaItem[] = [
  {
    rank: 1,
    t: 1320,
    label: "fight",
    title: "Baron pit ace — 5-0 into Baron",
    context: "Gold diff: +6,100 | All 5 TP'd in",
    what_to_watch:
      "Watch engage timing from Nautilus and how Aatrox chains the dive onto LeBlanc. Clean execution; replicate for next scrims.",
  },
  {
    rank: 2,
    t: 540,
    label: "fight",
    title: "River top 2-0 fight → Herald",
    context: "Gold diff: +700 | Graves + Aatrox first clear synced",
    what_to_watch:
      "Graves early invade forces Lee Sin to commit. Note the vision setup pre-fight and the immediate Herald pickup.",
  },
  {
    rank: 3,
    t: 480,
    label: "objective",
    title: "First dragon — infernal",
    context: "Gold diff: +800 | Unopposed",
    what_to_watch:
      "Red side made no contest. Check if this was a vision mistake or a decision to trade elsewhere.",
  },
  {
    rank: 4,
    t: 840,
    label: "fight",
    title: "Mid 4v1 dive → outer tower",
    context: "Gold diff: +2,300 | LeBlanc solo vs 4",
    what_to_watch:
      "Azir wave management before the dive creates the opportunity. Bot lane roam timing with Jinx + Nautilus.",
  },
  {
    rank: 5,
    t: 720,
    label: "objective",
    title: "Herald pickup post-river fight",
    context: "Gold diff: +1,700 | Unopposed",
    what_to_watch:
      "Herald placed mid creates the lane pressure that snowballs Azir's advantage. Study the plate damage.",
  },
];
