"""
LLM agent using Ollama for local inference.

Privacy guarantee: this module sends ONLY pre-aggregated, derived data to
Ollama, which runs entirely on the local machine. Raw game payloads, player
identities, and ungated rows never leave the box.

The LLM role is narration only — all quantitative work is done by
build_digest() (per game) or DuckDB SQL (across games). The model never
performs arithmetic on its own.

Two public functions:
  generate_agenda(digest)         → list[AgendaItem]
  answer_question(question, conn) → QAResponse   (two-stage text-to-SQL)
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import duckdb
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.digest.models import GameDigest
from app.llm.sql import (
    MAX_LIMIT,
    SCHEMA_DESCRIPTION,
    SqlValidationError,
    run_safe_select,
    validate_select,
)

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

_SQL_GEN_SYSTEM = """\
You translate analyst questions into DuckDB SELECT queries over a fixed schema. \
Rules: ONLY a single SELECT (or WITH ... SELECT). No INSERT, UPDATE, DELETE, \
DROP, ALTER, CREATE, ATTACH, COPY, PRAGMA, or any other side-effecting keyword. \
Reference only the listed tables. Prefer aggregation (AVG, SUM, COUNT, etc.). \
Include game_id in the SELECT when individual games are relevant. \
Return ONLY JSON of the form {"sql": "SELECT ..."} — no markdown, no commentary."""

_SQL_GEN_USER = """\
{schema}

Question: {question}

Return JSON: {{"sql": "SELECT ..."}}"""

_NARRATE_SYSTEM = """\
You narrate the result of a DuckDB query for a League of Legends analyst. \
Base your answer ONLY on the rows provided. Do not invent numbers. If rows are \
empty, say so plainly. Return ONLY JSON of the form {"answer": "..."}."""

_NARRATE_USER = """\
Question: {question}

Query rows ({n} returned, columns: {columns}):
{rows_json}

Return JSON: {{"answer": "<focused prose answer>"}}"""


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


async def _ollama_chat_json(system: str, user: str) -> dict[str, Any]:
    """
    Send a single chat turn to Ollama with format=json and return the parsed dict.

    Raises:
        ImportError  — ollama package missing.
        asyncio.TimeoutError — model didn't respond within settings.ollama_timeout_s.
        json.JSONDecodeError | ValueError — model returned no/invalid JSON.
        Exception — network / Ollama-side errors (caller decides).
    """
    import ollama  # lazy: keep the app importable without the package present

    client = ollama.AsyncClient(host=settings.ollama_host)
    response = await asyncio.wait_for(
        client.chat(
            model=settings.ollama_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            format="json",
        ),
        timeout=settings.ollama_timeout_s,
    )
    raw_content = response.message.content
    if not raw_content:
        raise ValueError("Ollama returned empty content")
    parsed = json.loads(raw_content)
    if not isinstance(parsed, dict):
        raise ValueError(f"Ollama returned non-object JSON: {type(parsed).__name__}")
    return parsed


async def _generate_sql(question: str) -> str:
    """Ask the LLM for a SELECT statement answering `question`. Patched in tests."""
    parsed = await _ollama_chat_json(
        system=_SQL_GEN_SYSTEM,
        user=_SQL_GEN_USER.format(schema=SCHEMA_DESCRIPTION, question=question),
    )
    sql = parsed.get("sql", "")
    if not isinstance(sql, str):
        raise ValueError("Ollama returned non-string `sql` field")
    return sql


async def _narrate_sql_result(
    question: str,
    columns: list[str],
    rows: list[tuple[Any, ...]],
) -> str:
    """Ask the LLM to narrate the SQL result rows. Patched in tests."""
    # Cap rows in the prompt to keep tokens low even if the validator allowed up to MAX_LIMIT.
    rows_for_prompt = [dict(zip(columns, _jsonable(row), strict=True)) for row in rows[:MAX_LIMIT]]
    parsed = await _ollama_chat_json(
        system=_NARRATE_SYSTEM,
        user=_NARRATE_USER.format(
            question=question,
            n=len(rows),
            columns=", ".join(columns) or "(none)",
            rows_json=json.dumps(rows_for_prompt, default=str),
        ),
    )
    answer = parsed.get("answer", "")
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError("Ollama returned no `answer` field")
    return answer


def _jsonable(row: tuple[Any, ...]) -> list[Any]:
    """Convert DuckDB row cells (Decimal, datetime, etc.) into JSON-safe primitives."""
    out: list[Any] = []
    for cell in row:
        if cell is None or isinstance(cell, (str, int, float, bool)):
            out.append(cell)
        else:
            out.append(str(cell))
    return out


def _extract_game_ids(columns: list[str], rows: list[tuple[Any, ...]]) -> list[str]:
    """If the result set has a game_id column, return distinct values preserving order."""
    if "game_id" not in columns:
        return []
    idx = columns.index("game_id")
    seen: set[str] = set()
    out: list[str] = []
    for row in rows:
        gid = row[idx]
        if isinstance(gid, str) and gid not in seen:
            seen.add(gid)
            out.append(gid)
    return out


def _fallback_qa_answer(reason: str, games_in_db: int) -> QAResponse:
    """Construct a graceful-degradation QAResponse the frontend can display."""
    if games_in_db == 0:
        return QAResponse(
            answer="No games in the database yet. Run the seed script to ingest some matches.",
            game_ids_referenced=[],
        )
    return QAResponse(
        answer=(
            f"{reason} Found {games_in_db} game(s) in the database — "
            "try rephrasing or check that Ollama is running (`ollama serve`)."
        ),
        game_ids_referenced=[],
    )


# ── Public functions ──────────────────────────────────────────────────────────


async def generate_agenda(digest: GameDigest) -> list[AgendaItem]:
    """
    Generate a ranked review agenda from a GameDigest using the local Ollama model.

    Falls back to a mechanical agenda if Ollama is unreachable, times out, or
    returns unusable output. Each failure mode logs distinctly so the operator
    can tell "Ollama is down" from "Ollama returned garbage".
    """
    try:
        import ollama  # imported lazily so the app starts without the package
    except ImportError:
        logger.warning("ollama package not installed — using fallback agenda")
        return _fallback_agenda(digest)

    try:
        client = ollama.AsyncClient(host=settings.ollama_host)
        prompt = _AGENDA_USER.format(digest_json=_compact_digest(digest))
        response = await asyncio.wait_for(
            client.chat(
                model=settings.ollama_model,
                messages=[
                    {"role": "system", "content": _AGENDA_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                format="json",
            ),
            timeout=settings.ollama_timeout_s,
        )
        raw_content = response.message.content
        if not raw_content:
            raise ValueError("Ollama returned empty content")
        parsed = json.loads(raw_content)
        # Handle both {"items": [...]} and bare [...] responses
        items_raw: list[Any] = parsed if isinstance(parsed, list) else parsed.get("items", [])
        items = [AgendaItem.model_validate(item) for item in items_raw]
        if not items:
            raise ValueError("Empty agenda from LLM")
        logger.info("Agenda generated by Ollama: %d items", len(items))
        return items
    except asyncio.TimeoutError:
        logger.warning(
            "Ollama timed out after %ds — using fallback agenda", settings.ollama_timeout_s
        )
    except (json.JSONDecodeError, ValidationError, ValueError, AttributeError) as exc:
        logger.warning(
            "LLM returned unusable output (%s: %s) — using fallback agenda",
            type(exc).__name__,
            exc,
        )
    except Exception as exc:
        # ollama.ResponseError, httpx.HTTPError, ConnectionError, OSError, etc.
        logger.warning(
            "Ollama unreachable (%s: %s) — using fallback agenda", type(exc).__name__, exc
        )
    return _fallback_agenda(digest)


async def answer_question(
    question: str,
    conn: duckdb.DuckDBPyConnection,
) -> QAResponse:
    """
    Two-stage text-to-SQL Q&A over the derived DuckDB tables.

    1. Ask Ollama for a SELECT translating the question against SCHEMA_DESCRIPTION.
    2. Run it through validate_select() — the SQL is rejected if it touches any
       table outside the whitelist, contains forbidden keywords, has comments,
       or is more than a single statement.
    3. Execute the validated SQL on a fresh cursor (read-only by construction —
       the validator is the only path that produces executable SQL).
    4. Ask Ollama to narrate the rows in plain prose.

    Any failure (Ollama down, validation fails, execution fails, narration
    fails) falls back to a graceful-degradation message; QAResponse shape
    is preserved.
    """
    games_in_db = _count_games(conn)
    if games_in_db == 0:
        return _fallback_qa_answer("", games_in_db=0)

    # ── Stage 1: SQL generation ──
    try:
        raw_sql = await _generate_sql(question)
    except ImportError:
        logger.warning("ollama package not installed — Q&A fallback")
        return _fallback_qa_answer("Ollama is not installed.", games_in_db)
    except asyncio.TimeoutError:
        logger.warning("Ollama timed out on SQL generation after %ds", settings.ollama_timeout_s)
        return _fallback_qa_answer(
            f"The model did not respond within {settings.ollama_timeout_s}s.", games_in_db
        )
    except (json.JSONDecodeError, ValueError, AttributeError, ValidationError) as exc:
        logger.warning("SQL generation returned unusable output (%s: %s)", type(exc).__name__, exc)
        return _fallback_qa_answer("Could not generate a query for that question.", games_in_db)
    except Exception as exc:
        logger.warning("Ollama unreachable during SQL generation (%s: %s)", type(exc).__name__, exc)
        return _fallback_qa_answer("Ollama is not available.", games_in_db)

    # ── Stage 2: validate ──
    try:
        safe_sql = validate_select(raw_sql)
    except SqlValidationError as exc:
        logger.warning("Rejected generated SQL (%s): %r", exc, raw_sql)
        return _fallback_qa_answer("The generated query did not pass safety checks.", games_in_db)

    # ── Stage 3: execute ──
    try:
        columns, rows = run_safe_select(conn, safe_sql)
    except duckdb.Error as exc:
        logger.warning("DuckDB rejected safe SQL (%s): %s", type(exc).__name__, exc)
        return _fallback_qa_answer("The query failed to execute.", games_in_db)

    logger.info("Q&A SQL: %s  →  %d rows", safe_sql, len(rows))

    if not rows:
        return QAResponse(
            answer="The query returned no rows. Try rephrasing or broadening the question.",
            game_ids_referenced=[],
        )

    # ── Stage 4: narrate ──
    referenced = _extract_game_ids(columns, rows)
    try:
        answer = await _narrate_sql_result(question, columns, rows)
    except ImportError:
        return _fallback_qa_answer("Ollama is not installed.", games_in_db)
    except asyncio.TimeoutError:
        logger.warning("Ollama timed out on narration after %ds", settings.ollama_timeout_s)
        return QAResponse(
            answer=(
                f"Query returned {len(rows)} row(s) but the model did not narrate "
                f"within {settings.ollama_timeout_s}s."
            ),
            game_ids_referenced=referenced,
        )
    except (json.JSONDecodeError, ValueError, AttributeError, ValidationError) as exc:
        logger.warning("Narration returned unusable output (%s: %s)", type(exc).__name__, exc)
        return QAResponse(
            answer=f"Query returned {len(rows)} row(s) but the model could not summarize them.",
            game_ids_referenced=referenced,
        )
    except Exception as exc:
        logger.warning("Ollama unreachable during narration (%s: %s)", type(exc).__name__, exc)
        return QAResponse(
            answer=f"Query returned {len(rows)} row(s) but Ollama is not available to narrate.",
            game_ids_referenced=referenced,
        )

    return QAResponse(answer=answer, game_ids_referenced=referenced)


def _count_games(conn: duckdb.DuckDBPyConnection) -> int:
    row = conn.execute("SELECT COUNT(*) FROM games").fetchone()
    return int(row[0]) if row else 0
