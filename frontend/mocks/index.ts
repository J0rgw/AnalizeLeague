import type { GameSummary, AgendaItem, QAResponse } from "@/lib/api";
import type { GameDigest } from "@/types/digest";

import {
  victorySummary,
  victoryDigest,
  victoryAgenda,
} from "./game-victory";
import {
  baronThrowSummary,
  baronThrowDigest,
  baronThrowAgenda,
} from "./game-baron-throw";
import {
  closeSummary,
  closeDigest,
  closeAgenda,
} from "./game-close";

export const MOCK_SUMMARIES: GameSummary[] = [
  victorySummary,
  baronThrowSummary,
  closeSummary,
];

const MOCK_DIGESTS: Record<string, GameDigest> = {
  [victorySummary.game_id]:    victoryDigest,
  [baronThrowSummary.game_id]: baronThrowDigest,
  [closeSummary.game_id]:      closeDigest,
};

const MOCK_AGENDAS: Record<string, AgendaItem[]> = {
  [victorySummary.game_id]:    victoryAgenda,
  [baronThrowSummary.game_id]: baronThrowAgenda,
  [closeSummary.game_id]:      closeAgenda,
};

export function getMockDigest(gameId: string): GameDigest {
  const digest = MOCK_DIGESTS[gameId];
  if (!digest) throw new Error(`No mock digest for game ID: ${gameId}`);
  return digest;
}

export function getMockAgenda(gameId: string): AgendaItem[] {
  const agenda = MOCK_AGENDAS[gameId];
  if (!agenda) throw new Error(`No mock agenda for game ID: ${gameId}`);
  return agenda;
}

const QA_RESPONSES: { keywords: string[]; answer: string }[] = [
  {
    keywords: ["baron", "throw"],
    answer:
      "In scrim-2025-w20-g2 (Patch 14.10, red side) your team held a +5,200 gold advantage at minute 26 but entered Baron at minute 35 with only +300 gold and no vision control. Kindred's ult nullified your engage and you were aced 0-5. The key mistake was initiating Baron without clearing the pit wards — blue team had a deep ward in baron bush that gave them the angle.",
  },
  {
    keywords: ["jungle", "path"],
    answer:
      "This week your jungler opened red → raptors → wolves → blue in games 1 and 3, and red → raptors → wolves → blue → gromp in game 2. The main difference vs opponents: you prioritize rift scuttler control (taken in all 3 games), while opponents leaned toward early gank pressure. Hecarim's level 3 full-clear is slower than Nidalee's full-clear by ~18s on average.",
  },
  {
    keywords: ["dragon", "soul"],
    answer:
      "You lost dragon soul in scrim-2025-w21-g1. The hextech dragon at minute 33 was contested but lost 2-2 in fight trades, then red secured the soul at minute 39. Your team had vision of the pit but Hecarim was on the wrong side. Review the minute 33 dragon fight — the engage angle was poor and Orianna's ball was out of range for a decisive shockwave.",
  },
  {
    keywords: ["map control", "vision"],
    answer:
      "Across 3 scrims this week, your team averaged 4.2 wards placed per minute vs opponent's 3.8. However, you cleared only 61% of enemy wards found. The baron pit was unvision'd in the key fight of game 2 despite having 40 seconds of warning. Vision around neutral objectives remains the primary area for improvement.",
  },
];

export function getMockQAResponse(question: string): QAResponse {
  const q = question.toLowerCase();
  for (const entry of QA_RESPONSES) {
    if (entry.keywords.some((k) => q.includes(k))) {
      return {
        answer: entry.answer,
        game_ids_referenced: MOCK_SUMMARIES.map((s) => s.game_id),
      };
    }
  }
  return {
    answer:
      "Based on this week's 3 scrims (Patch 14.10–14.11), your team's main strengths are early jungle pressure and mid-game teamfight execution. The critical area to address is Baron pit vision control — two of the three games had critical objective fights with insufficient vision setup. I recommend reviewing the minute 35 baron fight from scrim-2025-w20-g2 first.",
    game_ids_referenced: MOCK_SUMMARIES.map((s) => s.game_id),
  };
}
