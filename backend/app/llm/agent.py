"""
LLM agent using Ollama for local inference.

Privacy guarantee: this module sends ONLY the compact GameDigest JSON to
Ollama, which runs entirely on the local machine. Raw game data and player
identities are never transmitted to any external service.

The LLM role is narration only — all quantitative analysis was already
done by build_digest(). See /.ai/architecture.md for the design rationale.

Two public functions:
  generate_agenda(digest)         → list[AgendaItem]
  answer_question(question, conn) → QAResponse
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, ValidationError

from app.config import settings
from app.digest.models import GameDigest

logger = logging.getLogger(__name__)

# ── Response models (also used by api/routes.py) ──────────────────────────────


class AgendaItem(BaseModel):
    rank: int
    t: int  # timestamp in seconds
    label: str  # "fight" | "objective" | "lane" | "jungle" | "recall"
    title: str
    context: str
    what_to_watch: str


class QAResponse(BaseModel):
    answer: str
    game_ids_referenced: list[str]


# ── Prompts ───────────────────────────────────────────────────────────────────

_AGENDA_SYSTEM = """\
You are a League of Legends coaching assistant. Your job is to select and narrate \
game moments from pre-computed data. Do NOT invent, modify, or extrapolate any \
numbers — every statistic in your answer must come directly from the GameDigest \
provided. Return ONLY valid JSON, no markdown, no explanation outside the JSON."""

_AGENDA_USER = """\
Given this GameDigest, return a JSON array of 6–8 review moments ranked by \
coaching value (most important first). Use only data present in the digest.

Required format (return ONLY this array):
[
  {{
    "rank": 1,
    "t": <integer seconds>,
    "label": "<fight|objective|lane|jungle|recall>",
    "title": "<short title, max 60 chars>",
    "context": "<2–3 sentences describing what happened based on the data>",
    "what_to_watch": "<1–2 sentences on what to look for in the replay>"
  }}
]

GameDigest:
{digest_json}"""

_QA_SYSTEM = """\
You are a League of Legends coaching assistant. Answer the analyst's question \
based ONLY on the provided game data. Do not invent statistics. If the answer is \
not in the data, say so explicitly. Return ONLY valid JSON."""

_QA_USER = """\
Question: {question}

Available game data ({n} games):
{summaries}

Return JSON:
{{"answer": "<your answer>", "game_ids_referenced": ["<game_id>", ...]}}"""


# ── Fallback (no LLM) ─────────────────────────────────────────────────────────


def _fallback_agenda(digest: GameDigest) -> list[AgendaItem]:
    """Generate a mechanical agenda when Ollama is unavailable."""
    items: list[AgendaItem] = []
    rank = 1

    # Top 3 fights by absolute gold swing
    sorted_fights = sorted(digest.fights, key=lambda f: abs(f.gold_swing), reverse=True)
    for fight in sorted_fights[:3]:
        direction = "gained" if fight.gold_swing >= 0 else "lost"
        items.append(
            AgendaItem(
                rank=rank,
                t=fight.t,
                label="fight",
                title=f"Fight at {fight.where} ({fight.kills_for}v{fight.kills_against})",
                context=(
                    f"A fight at {fight.where} resulted in {fight.kills_for} kills for our "
                    f"team and {fight.kills_against} against. "
                    f"Gold swing: {abs(fight.gold_swing):,} {direction}."
                ),
                what_to_watch=(
                    f"Review positioning going into the fight and "
                    f"{'the follow-up on ' + fight.led_to if fight.led_to else 'the macro aftermath'}."
                ),
            )
        )
        rank += 1

    # Worst lane state at 14 min
    worst_lane = min(
        (ls for ls in digest.lane_states if ls.at_min == 14),
        key=lambda ls: ls.gold_diff,
        default=None,
    )
    if worst_lane and worst_lane.gold_diff < -500:
        items.append(
            AgendaItem(
                rank=rank,
                t=14 * 60,
                label="lane",
                title=f"{worst_lane.lane.upper()} lane at 14 min ({worst_lane.gold_diff:+}g)",
                context=(
                    f"At 14 minutes the {worst_lane.lane} lane was {abs(worst_lane.gold_diff):,}g "
                    f"behind with CS diff of {worst_lane.cs_diff:+}."
                ),
                what_to_watch="Review the 8–14 min window to understand how this deficit developed.",
            )
        )
        rank += 1

    # Baron / Herald objectives
    for obj in digest.objectives:
        if obj.type in ("baron", "herald") and rank <= 8:
            taken_by = "our team" if obj.team == digest.meta.side else "opponent"
            items.append(
                AgendaItem(
                    rank=rank,
                    t=obj.t,
                    label="objective",
                    title=f"{obj.type.capitalize()} taken by {taken_by}",
                    context=(
                        f"{obj.type.capitalize()} secured by {obj.team} side at "
                        f"{obj.t // 60}:{obj.t % 60:02d}. "
                        f"Gold diff at event: {obj.gold_diff_at_event:+}. "
                        + (f"Tradeoff: {obj.tradeoff}." if obj.tradeoff else "")
                    ),
                    what_to_watch=(
                        "Review the setup, vision control, and whether the trade was worth it."
                    ),
                )
            )
            rank += 1

    return items[:8]


# ── Ollama helpers ────────────────────────────────────────────────────────────


def _compact_digest(digest: GameDigest) -> str:
    """Serialize digest to compact JSON (~2 KB target)."""
    return digest.model_dump_json(exclude_none=True)


def _digest_summary_for_qa(digest: GameDigest) -> dict[str, Any]:
    """Produce a compressed summary dict for multi-game Q&A context."""
    return {
        "game_id": digest.meta.game_id,
        "patch": digest.meta.patch,
        "result": digest.meta.result,
        "side": digest.meta.side,
        "duration_min": round(digest.meta.duration_s / 60, 1),
        "draft_blue": digest.draft.blue.model_dump(),
        "draft_red": digest.draft.red.model_dump(),
        "gold_diff_at_20min": (
            digest.team_gold_diff_by_min[20] if len(digest.team_gold_diff_by_min) > 20 else None
        ),
        "objectives": [
            {"t": o.t, "type": o.type, "subtype": o.subtype, "team": o.team}
            for o in digest.objectives
        ],
        "fights_count": len(digest.fights),
        "lane_states_14min": [
            {"lane": ls.lane, "gold_diff": ls.gold_diff}
            for ls in digest.lane_states
            if ls.at_min == 14
        ],
    }


# ── Public functions ──────────────────────────────────────────────────────────


async def generate_agenda(digest: GameDigest) -> list[AgendaItem]:
    """
    Generate a ranked review agenda from a GameDigest using the local Ollama model.

    Falls back to a mechanical agenda if Ollama is unavailable or returns bad JSON.
    """
    try:
        import ollama  # imported lazily so the app starts without Ollama running

        client = ollama.AsyncClient(host=settings.ollama_host)
        prompt = _AGENDA_USER.format(digest_json=_compact_digest(digest))
        response = await client.chat(
            model=settings.ollama_model,
            messages=[
                {"role": "system", "content": _AGENDA_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            format="json",
        )
        raw_content: str = response.message.content
        parsed = json.loads(raw_content)
        # Handle both {"items": [...]} and bare [...] responses
        items_raw: list[Any] = parsed if isinstance(parsed, list) else parsed.get("items", [])
        items = [AgendaItem.model_validate(item) for item in items_raw]
        if not items:
            raise ValueError("Empty agenda from LLM")
        logger.info("Agenda generated by Ollama: %d items", len(items))
        return items

    except (ImportError, Exception) as exc:
        logger.warning("Ollama unavailable (%s) — using fallback agenda", exc)
        return _fallback_agenda(digest)


async def answer_question(
    question: str,
    digests: list[GameDigest],
) -> QAResponse:
    """
    Answer a natural-language question about stored games using the local Ollama model.

    Args:
        question: Free-text question from the analyst.
        digests:  List of recent GameDigests to use as context.
    """
    summaries = [_digest_summary_for_qa(d) for d in digests]
    summaries_json = json.dumps(summaries, indent=2)

    try:
        import ollama

        client = ollama.AsyncClient(host=settings.ollama_host)
        prompt = _QA_USER.format(
            question=question,
            n=len(digests),
            summaries=summaries_json,
        )
        response = await client.chat(
            model=settings.ollama_model,
            messages=[
                {"role": "system", "content": _QA_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            format="json",
        )
        raw_content = response.message.content
        parsed = json.loads(raw_content)
        return QAResponse.model_validate(parsed)

    except ValidationError as exc:
        logger.warning("LLM returned invalid Q&A schema: %s", exc)
        return QAResponse(
            answer="Could not parse a structured answer from the model. Please rephrase.",
            game_ids_referenced=[],
        )
    except (ImportError, Exception) as exc:
        logger.warning("Ollama unavailable for Q&A (%s)", exc)
        return QAResponse(
            answer=(
                f"Ollama is not available. "
                f"Found {len(digests)} game(s) in the database. "
                f"Start Ollama and retry: `ollama serve`."
            ),
            game_ids_referenced=[],
        )
