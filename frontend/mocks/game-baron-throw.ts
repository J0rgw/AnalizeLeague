import type { GameDigest } from "@/types/digest";
import type { AgendaItem, GameSummary } from "@/lib/api";

export const baronThrowSummary: GameSummary = {
  game_id: "scrim-2025-w20-g2",
  patch: "14.10",
  duration_s: 2220,
  side: "red",
  result: "loss",
};

export const baronThrowDigest: GameDigest = {
  meta: {
    game_id: "scrim-2025-w20-g2",
    patch: "14.10",
    duration_s: 2220,
    side: "red",
    result: "loss",
  },
  draft: {
    blue: { top: "Sion",   jng: "Kindred", mid: "Viktor",  bot: "Aphelios", sup: "Lulu"  },
    red:  { top: "Gragas", jng: "Bel'Veth", mid: "Syndra",  bot: "Jhin",     sup: "Rakan" },
    bans: {
      blue: ["Azir", "Graves", "Nautilus", "Jinx", "Thresh"],
      red:  ["Renekton", "Lee Sin", "Aatrox", "Orianna", "Kalista"],
    },
  },
  lane_states: [
    // Minute 8
    { at_min: 8, lane: "top", gold_diff: -100, cs_diff: -3, xp_diff:  -60, kills: 0 },
    { at_min: 8, lane: "jng", gold_diff:  300, cs_diff:  8, xp_diff:   90, kills: 1 },
    { at_min: 8, lane: "mid", gold_diff:  200, cs_diff:  5, xp_diff:   40, kills: 0 },
    { at_min: 8, lane: "bot", gold_diff:  150, cs_diff:  3, xp_diff:   20, kills: 0 },
    { at_min: 8, lane: "sup", gold_diff:   50, cs_diff:  0, xp_diff:   10, kills: 0 },
    // Minute 14
    { at_min: 14, lane: "top", gold_diff: -200, cs_diff:  -8, xp_diff: -120, kills: 0 },
    { at_min: 14, lane: "jng", gold_diff:  700, cs_diff:  18, xp_diff:  200, kills: 2 },
    { at_min: 14, lane: "mid", gold_diff:  600, cs_diff:  15, xp_diff:  150, kills: 1 },
    { at_min: 14, lane: "bot", gold_diff:  400, cs_diff:  10, xp_diff:   80, kills: 1 },
    { at_min: 14, lane: "sup", gold_diff:  150, cs_diff:   0, xp_diff:   40, kills: 1 },
    // Minute 20
    { at_min: 20, lane: "top", gold_diff: -300, cs_diff: -12, xp_diff: -200, kills: 0 },
    { at_min: 20, lane: "jng", gold_diff: 1200, cs_diff:  25, xp_diff:  300, kills: 3 },
    { at_min: 20, lane: "mid", gold_diff: 1100, cs_diff:  22, xp_diff:  280, kills: 2 },
    { at_min: 20, lane: "bot", gold_diff:  800, cs_diff:  18, xp_diff:  160, kills: 2 },
    { at_min: 20, lane: "sup", gold_diff:  300, cs_diff:   0, xp_diff:   80, kills: 2 },
  ],
  // Red side ahead from minute 5 to 34; catastrophic loss at minute 35 (baron fight)
  team_gold_diff_by_min: [
    0, 0, -100, 0, 100, 300, 500, 700, 900,
    1100, 1300, 1500, 1700, 2000, 2300, 2600,
    3000, 3400, 3800, 4200, 4600, 5000, 5200,
    5000, 4800, 4600, 5200, 5200, 5000, 4800,
    4500, 4200, 3800, 3200, 2400, 300, -4500, -7000,
  ],
  objectives: [
    { t:  540, type: "dragon",    subtype: "cloud",    team: "red",  gold_diff_at_event:  600, tradeoff: "" },
    { t:  780, type: "herald",    subtype: "",          team: "red",  gold_diff_at_event: 1100, tradeoff: "" },
    { t: 1260, type: "dragon",    subtype: "infernal",  team: "red",  gold_diff_at_event: 4200, tradeoff: "" },
    { t: 1560, type: "baron",     subtype: "",          team: "red",  gold_diff_at_event: 5200, tradeoff: "" },
    { t: 1800, type: "dragon",    subtype: "ocean",     team: "red",  gold_diff_at_event: 4500, tradeoff: "blue team took top tower" },
    { t: 2100, type: "baron",     subtype: "",          team: "blue", gold_diff_at_event:   300, tradeoff: "red team aced 0-5 in baron pit; blue took uncontested" },
    { t: 2160, type: "inhibitor", subtype: "mid",       team: "blue", gold_diff_at_event: -5000, tradeoff: "" },
  ],
  fights: [
    {
      t: 540, where: "river_bot",
      kills_for: 1, kills_against: 0, gold_swing:  400,
      led_to: "dragon",
      players_near: ["jng", "bot", "sup"],
    },
    {
      t: 1020, where: "mid_lane",
      kills_for: 3, kills_against: 0, gold_swing: 1200,
      led_to: "",
      players_near: ["jng", "mid", "bot", "sup"],
    },
    {
      t: 1560, where: "baron_pit",
      kills_for: 4, kills_against: 0, gold_swing: 2000,
      led_to: "baron",
      players_near: ["top", "jng", "mid", "bot", "sup"],
    },
    {
      t: 2100, where: "baron_pit",
      kills_for: 0, kills_against: 5, gold_swing: -5000,
      led_to: "baron_opponent",
      players_near: ["top", "jng", "mid", "bot", "sup"],
    },
  ],
  jungle_path: {
    blue: ["blue_buff", "gromp", "wolves", "red_buff", "krugs", "rift_scuttler_bot"],
    red:  ["red_buff", "raptors", "wolves", "blue_buff", "gromp", "rift_scuttler_top"],
  },
  recalls: [
    { player: "red_top", t:  720, synced_with_team: false },
    { player: "red_jng", t:  750, synced_with_team: true  },
    { player: "red_mid", t:  780, synced_with_team: true  },
    { player: "red_bot", t: 1620, synced_with_team: true  },
    { player: "red_sup", t: 1620, synced_with_team: true  },
    { player: "red_top", t: 1680, synced_with_team: false },
  ],
};

export const baronThrowAgenda: AgendaItem[] = [
  {
    rank: 1,
    t: 2100,
    label: "fight",
    title: "CRITICAL — Baron pit aced 0-5 → game lost",
    context: "Gold diff: +300 | Red had +5,000 gold lead 5 min earlier",
    what_to_watch:
      "Why did red initiate Baron at +300 instead of waiting to stabilize? Rakan's engage angle, vision control before the pit. Blue Kindred ult timing nullifies the fight.",
  },
  {
    rank: 2,
    t: 1800,
    label: "objective",
    title: "Dragon soul (ocean) while gold lead erodes",
    context: "Gold diff: +4,500 | Blue pressure top side",
    what_to_watch:
      "Red secured dragon soul but blue contested top side. Was this the right split? Gold lead dropped 700 in that minute.",
  },
  {
    rank: 3,
    t: 1560,
    label: "fight",
    title: "First Baron — 4-0 ace → clean execute",
    context: "Gold diff: +5,200 | All 5 members alive",
    what_to_watch:
      "Contrast this with the second Baron fight. Identical setup but different outcome — what changed in vision and engage conditions?",
  },
  {
    rank: 4,
    t: 1020,
    label: "fight",
    title: "Mid 3-0 teamfight — peak momentum",
    context: "Gold diff: +3,800 | Red at maximum aggression",
    what_to_watch:
      "Syndra stun chain into Jhin W setup. This is the fight that built the lead. Note Bel'Veth target selection.",
  },
  {
    rank: 5,
    t: 1260,
    label: "objective",
    title: "Infernal dragon — soul stack 2",
    context: "Gold diff: +4,200 | Unopposed",
    what_to_watch:
      "Red walked the dragon free after mid fight. Check if blue had any answer or simply mispositioned.",
  },
  {
    rank: 6,
    t: 540,
    label: "objective",
    title: "First dragon + river skirmish",
    context: "Gold diff: +600 | Bel'Veth first clear advantage",
    what_to_watch:
      "Bel'Veth early clear speed creates bot pressure. Note how Rakan roam timing syncs with Bel'Veth.",
  },
];
