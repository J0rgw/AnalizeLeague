import type { GameDigest } from "@/types/digest";
import type { AgendaItem, GameSummary } from "@/lib/api";

export const closeSummary: GameSummary = {
  game_id: "scrim-2025-w21-g1",
  patch: "14.11",
  duration_s: 2700,
  side: "blue",
  result: "loss",
};

export const closeDigest: GameDigest = {
  meta: {
    game_id: "scrim-2025-w21-g1",
    patch: "14.11",
    duration_s: 2700,
    side: "blue",
    result: "loss",
  },
  draft: {
    blue: { top: "Garen",   jng: "Hecarim",  mid: "Orianna",  bot: "Ezreal",  sup: "Yuumi"  },
    red:  { top: "Fiora",   jng: "Nidalee",  mid: "Zed",      bot: "Draven",  sup: "Pyke"   },
    bans: {
      blue: ["LeBlanc", "Syndra",   "Jinx",     "Caitlyn",  "Nautilus"],
      red:  ["Azir",    "Viktor",   "Graves",   "Bel'Veth", "Lulu"],
    },
  },
  lane_states: [
    // Minute 8 — blue slightly ahead in jungle, red winning top/bot
    { at_min: 8, lane: "top", gold_diff: -300, cs_diff:  -5, xp_diff: -100, kills: 0 },
    { at_min: 8, lane: "jng", gold_diff:  200, cs_diff:   6, xp_diff:   60, kills: 0 },
    { at_min: 8, lane: "mid", gold_diff:  100, cs_diff:   2, xp_diff:   20, kills: 0 },
    { at_min: 8, lane: "bot", gold_diff: -200, cs_diff:  -4, xp_diff:  -40, kills: 0 },
    { at_min: 8, lane: "sup", gold_diff:  -50, cs_diff:   0, xp_diff:  -10, kills: 0 },
    // Minute 14 — even game, slight blue deficit
    { at_min: 14, lane: "top", gold_diff: -800, cs_diff: -15, xp_diff: -280, kills: 0 },
    { at_min: 14, lane: "jng", gold_diff:  400, cs_diff:  10, xp_diff:  120, kills: 1 },
    { at_min: 14, lane: "mid", gold_diff:  300, cs_diff:   8, xp_diff:   80, kills: 0 },
    { at_min: 14, lane: "bot", gold_diff: -400, cs_diff:  -8, xp_diff:  -80, kills: 0 },
    { at_min: 14, lane: "sup", gold_diff: -100, cs_diff:   0, xp_diff:  -20, kills: 0 },
    // Minute 20 — blue slightly ahead via teamfight wins
    { at_min: 20, lane: "top", gold_diff: -600, cs_diff: -20, xp_diff: -350, kills: 0 },
    { at_min: 20, lane: "jng", gold_diff:  900, cs_diff:  18, xp_diff:  200, kills: 2 },
    { at_min: 20, lane: "mid", gold_diff:  700, cs_diff:  15, xp_diff:  180, kills: 2 },
    { at_min: 20, lane: "bot", gold_diff:  200, cs_diff:   4, xp_diff:   40, kills: 1 },
    { at_min: 20, lane: "sup", gold_diff:  100, cs_diff:   0, xp_diff:   20, kills: 1 },
  ],
  // Back-and-forth; blue peeks at +2000 around min 22, then slowly loses control late
  team_gold_diff_by_min: [
    0, -100, -200, -200, -100, 0, 100, 200, 300,
    400, 600, 800, 1000, 800, 600, 400, 600,
    800, 1000, 1200, 1500, 1800, 2000, 1800,
    1600, 1400, 1200, 1000, 800, 1000, 1200,
    1400, 1600, 1400, 1200, 1000, 800, 600,
    400, 200, -200, -600, -1000, -1500, -2000, -2500,
  ],
  objectives: [
    { t:  660, type: "herald",    subtype: "",         team: "blue", gold_diff_at_event:  400,  tradeoff: "" },
    { t:  900, type: "dragon",    subtype: "cloud",    team: "red",  gold_diff_at_event:  600,  tradeoff: "" },
    { t: 1380, type: "dragon",    subtype: "infernal", team: "blue", gold_diff_at_event: 1500,  tradeoff: "" },
    { t: 1680, type: "baron",     subtype: "",         team: "blue", gold_diff_at_event: 1800,  tradeoff: "" },
    { t: 1980, type: "dragon",    subtype: "hextech",  team: "red",  gold_diff_at_event: 1000,  tradeoff: "blue tried to contest but lost 2 members" },
    { t: 2160, type: "dragon",    subtype: "mountain", team: "red",  gold_diff_at_event:  400,  tradeoff: "" },
    { t: 2340, type: "baron",     subtype: "",         team: "red",  gold_diff_at_event: -1000, tradeoff: "blue caught rotating; Fiora split destroyed base" },
    { t: 2460, type: "inhibitor", subtype: "bot",      team: "red",  gold_diff_at_event: -2000, tradeoff: "" },
  ],
  fights: [
    {
      t: 660, where: "river_top",
      kills_for: 1, kills_against: 0, gold_swing: 400,
      led_to: "herald",
      players_near: ["jng", "top", "mid"],
    },
    {
      t: 1200, where: "mid_lane",
      kills_for: 2, kills_against: 1, gold_swing: 600,
      led_to: "",
      players_near: ["jng", "mid", "sup"],
    },
    {
      t: 1620, where: "baron_pit",
      kills_for: 3, kills_against: 2, gold_swing: 1000,
      led_to: "baron",
      players_near: ["top", "jng", "mid", "bot", "sup"],
    },
    {
      t: 1980, where: "dragon_pit",
      kills_for: 2, kills_against: 2, gold_swing: 0,
      led_to: "dragon_opponent",
      players_near: ["jng", "mid", "bot", "sup"],
    },
    {
      t: 2340, where: "baron_pit",
      kills_for: 1, kills_against: 3, gold_swing: -2000,
      led_to: "baron_opponent",
      players_near: ["top", "jng", "mid", "bot", "sup"],
    },
  ],
  jungle_path: {
    blue: ["blue_buff", "gromp", "wolves", "raptors", "red_buff", "rift_scuttler_bot"],
    red:  ["red_buff", "krugs", "raptors", "blue_buff", "wolves", "rift_scuttler_top"],
  },
  recalls: [
    { player: "blue_jng", t:  780, synced_with_team: true  },
    { player: "blue_mid", t:  780, synced_with_team: true  },
    { player: "blue_top", t:  900, synced_with_team: false },
    { player: "blue_bot", t: 1740, synced_with_team: true  },
    { player: "blue_sup", t: 1740, synced_with_team: true  },
    { player: "blue_top", t: 2040, synced_with_team: false },
  ],
};

export const closeAgenda: AgendaItem[] = [
  {
    rank: 1,
    t: 2340,
    label: "fight",
    title: "Second Baron — blue caught out 1-3",
    context: "Gold diff: +1,000 → -1,000 | Fiora split forcing bad fight",
    what_to_watch:
      "Blue walked into Baron without vision. Fiora's split-push created a catch situation. Why did the team contest instead of ceding Baron and defending?",
  },
  {
    rank: 2,
    t: 1980,
    label: "objective",
    title: "Hextech dragon contest — 2-2 trade",
    context: "Gold diff: +1,000 | Blue failed to secure dragon after winning fight",
    what_to_watch:
      "Blue won the fight 2-2 but lost the dragon. Resource management post-fight — who smited and why did they not prioritize the objective?",
  },
  {
    rank: 3,
    t: 1620,
    label: "fight",
    title: "Baron pit 3-2 — narrow win",
    context: "Gold diff: +1,800 | Orianna ball placement decisive",
    what_to_watch:
      "3-2 is a near-throw. Study Garen positioning — he died early and blue nearly lost the fight. Lucky Nidalee mispositioning.",
  },
  {
    rank: 4,
    t: 900,
    label: "objective",
    title: "Cloud dragon — red takes unopposed",
    context: "Gold diff: +600 | Blue top missing, Hecarim wrong side of map",
    what_to_watch:
      "Hecarim's position at minute 15 leaves the dragon uncontested. Is this a pathing issue or a comms failure?",
  },
  {
    rank: 5,
    t: 1200,
    label: "fight",
    title: "Mid 2-1 trade — slight blue advantage",
    context: "Gold diff: +800 | Orianna ult nets Zed",
    what_to_watch:
      "Good Orianna shockwave but Ezreal not in range to follow up. 2v1 roam could have been a 3v1 if bot teleported.",
  },
];
