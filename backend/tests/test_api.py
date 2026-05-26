"""
Integration tests for the FastAPI endpoints.

Uses the test_client fixture (in-memory DuckDB + TestClient).
Ollama is never started — generate_agenda falls back to the mechanical agenda,
and answer_question is mocked at the SQL-generation/narration boundary.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.digest.builder import build_digest
from app.llm import agent as agent_mod
from app.storage.db import save_game


def _seed(test_client: TestClient, raw: dict[str, Any]) -> str:
    """Insert a digest into the in-memory DB via the test client's app.state.db."""
    digest = build_digest(raw)
    save_game(test_client.app.state.db, digest)
    return digest.meta.game_id


# ── /health ───────────────────────────────────────────────────────────────────


def test_health(test_client: TestClient) -> None:
    resp = test_client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── GET /games ────────────────────────────────────────────────────────────────


def test_list_games_empty(test_client: TestClient) -> None:
    resp = test_client.get("/games")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_games_after_seed(test_client: TestClient, sample_raw_game: dict[str, Any]) -> None:
    _seed(test_client, sample_raw_game)
    resp = test_client.get("/games")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["game_id"] == "EUW1_TEST123"
    assert data[0]["result"] == "win"


# ── GET /games/{id}/digest ────────────────────────────────────────────────────


def test_get_digest_not_found(test_client: TestClient) -> None:
    resp = test_client.get("/games/EUW1_NOTFOUND/digest")
    assert resp.status_code == 404


def test_get_digest_invalid_id_format(test_client: TestClient) -> None:
    # Bare word fails the Riot match-ID regex enforced on the path param.
    resp = test_client.get("/games/NONEXISTENT/digest")
    assert resp.status_code == 422


def test_get_digest_ok(test_client: TestClient, sample_raw_game: dict[str, Any]) -> None:
    gid = _seed(test_client, sample_raw_game)
    resp = test_client.get(f"/games/{gid}/digest")
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["game_id"] == gid
    assert "draft" in body
    assert "lane_states" in body
    assert "fights" in body
    assert "objectives" in body
    assert isinstance(body["team_gold_diff_by_min"], list)


# ── GET /games/{id}/agenda ────────────────────────────────────────────────────


def test_get_agenda_not_found(test_client: TestClient) -> None:
    resp = test_client.get("/games/EUW1_NOTFOUND/agenda")
    assert resp.status_code == 404


def test_get_agenda_ok(test_client: TestClient, sample_raw_game: dict[str, Any]) -> None:
    gid = _seed(test_client, sample_raw_game)
    resp = test_client.get(f"/games/{gid}/agenda")
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    first = items[0]
    assert "rank" in first
    assert "t" in first
    assert "label" in first
    assert "title" in first
    assert "context" in first
    assert "what_to_watch" in first


def test_get_agenda_cached_on_second_call(
    test_client: TestClient, sample_raw_game: dict[str, Any]
) -> None:
    """Second call should return cached agenda from DuckDB."""
    gid = _seed(test_client, sample_raw_game)
    r1 = test_client.get(f"/games/{gid}/agenda")
    r2 = test_client.get(f"/games/{gid}/agenda")
    assert r1.status_code == 200
    assert r2.status_code == 200
    # Ranks should be identical
    assert r1.json()[0]["rank"] == r2.json()[0]["rank"]


# ── POST /ask ─────────────────────────────────────────────────────────────────


def test_ask_no_games(test_client: TestClient) -> None:
    resp = test_client.post("/ask", json={"question": "How did we play?"})
    assert resp.status_code == 200
    body = resp.json()
    assert "No games" in body["answer"]
    assert body["game_ids_referenced"] == []


def test_ask_falls_back_when_ollama_unavailable(
    test_client: TestClient, sample_raw_game: dict[str, Any]
) -> None:
    """With Ollama down, /ask still returns a structured QAResponse (no crash)."""
    _seed(test_client, sample_raw_game)
    resp = test_client.post("/ask", json={"question": "What was the gold diff at 14 minutes?"})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["answer"], str)
    assert isinstance(body["game_ids_referenced"], list)


def test_ask_end_to_end_with_mocked_llm(
    test_client: TestClient,
    sample_raw_game: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mock SQL gen + narration so the whole text-to-SQL pipeline runs end-to-end."""
    _seed(test_client, sample_raw_game)

    async def fake_generate_sql(_q: str) -> str:
        return "SELECT game_id, AVG(gold_diff) FROM lane_states WHERE at_min = 14 GROUP BY game_id"

    async def fake_narrate(question: str, columns: list[str], rows: list[Any]) -> str:
        return f"Saw {len(rows)} row(s) across columns {columns}."

    monkeypatch.setattr(agent_mod, "_generate_sql", fake_generate_sql)
    monkeypatch.setattr(agent_mod, "_narrate_sql_result", fake_narrate)

    resp = test_client.post("/ask", json={"question": "Average lane gold diff at 14?"})
    assert resp.status_code == 200
    body = resp.json()
    assert "row(s)" in body["answer"]
    assert "EUW1_TEST123" in body["game_ids_referenced"]


def test_ask_rejects_malicious_llm_sql(
    test_client: TestClient,
    sample_raw_game: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the LLM produces destructive SQL, the validator blocks it and the DB is intact."""
    _seed(test_client, sample_raw_game)

    async def evil_generate_sql(_q: str) -> str:
        return "DROP TABLE games"

    monkeypatch.setattr(agent_mod, "_generate_sql", evil_generate_sql)

    resp = test_client.post("/ask", json={"question": "Wipe my data."})
    assert resp.status_code == 200
    body = resp.json()
    # Fallback message, no crash, no data loss.
    assert "safety checks" in body["answer"]
    # Verify games table is still queryable.
    games_resp = test_client.get("/games")
    assert games_resp.status_code == 200
    assert len(games_resp.json()) == 1


def test_ask_question_too_long_returns_422(test_client: TestClient) -> None:
    resp = test_client.post("/ask", json={"question": "x" * 3000})
    assert resp.status_code == 422
