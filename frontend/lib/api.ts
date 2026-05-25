import type { GameDigest, Side, Result } from "@/types/digest";

// ────────────────────────────────────────────────────────────
// API response types (frontend contract with the backend)
// ────────────────────────────────────────────────────────────

export interface GameSummary {
  game_id: string;
  patch: string;
  duration_s: number;
  side: Side;
  result: Result;
}

export type AgendaLabel = "fight" | "objective" | "lane" | "jungle" | "recall";

export interface AgendaItem {
  rank: number;
  t: number;
  label: AgendaLabel;
  title: string;
  context: string;
  what_to_watch: string;
}

export interface QAResponse {
  answer: string;
  game_ids_referenced: string[];
}

// ────────────────────────────────────────────────────────────
// Config
// ────────────────────────────────────────────────────────────

const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === "true";
const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

// ────────────────────────────────────────────────────────────
// Helpers
// ────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

// Lazy-load mock helpers only when USE_MOCKS is true to avoid bundling them
// in production builds.
async function loadMocks() {
  return import("@/mocks/index");
}

// ────────────────────────────────────────────────────────────
// Public API functions
// ────────────────────────────────────────────────────────────

/** GET /games — returns summary list for the game selector view */
export async function listGames(): Promise<GameSummary[]> {
  if (USE_MOCKS) {
    const { MOCK_SUMMARIES } = await loadMocks();
    return MOCK_SUMMARIES;
  }
  return apiFetch<GameSummary[]>("/games");
}

/** GET /games/{id}/digest — full GameDigest for the detail view */
export async function getDigest(gameId: string): Promise<GameDigest> {
  if (USE_MOCKS) {
    const { getMockDigest } = await loadMocks();
    return getMockDigest(gameId);
  }
  return apiFetch<GameDigest>(`/games/${encodeURIComponent(gameId)}/digest`);
}

/** GET /games/{id}/agenda — ranked list of review moments */
export async function getAgenda(gameId: string): Promise<AgendaItem[]> {
  if (USE_MOCKS) {
    const { getMockAgenda } = await loadMocks();
    return getMockAgenda(gameId);
  }
  return apiFetch<AgendaItem[]>(`/games/${encodeURIComponent(gameId)}/agenda`);
}

/** POST /ask — natural-language Q&A over scrim history */
export async function askQuestion(question: string): Promise<QAResponse> {
  if (USE_MOCKS) {
    // Simulate a ~500ms "thinking" delay for realistic UX
    await new Promise((r) => setTimeout(r, 500));
    const { getMockQAResponse } = await loadMocks();
    return getMockQAResponse(question);
  }
  return apiFetch<QAResponse>("/ask", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}
