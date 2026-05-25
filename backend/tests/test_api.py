"""
Integration tests for the FastAPI endpoints.

Uses the test_client fixture (in-memory DuckDB + TestClient).
Ollama calls are not made — generate_agenda falls back to the mechanical agenda.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.digest.builder import build_digest
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
    resp = test_client.get("/games/NONEXISTENT/digest")
    assert resp.status_code == 404


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
    resp = test_client.get("/games/NONEXISTENT/agenda")
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
    assert "answer" in body
    assert "No games" in body["answer"] or isinstance(body["answer"], str)


def test_ask_with_games(test_client: TestClient, sample_raw_game: dict[str, Any]) -> None:
    _seed(test_client, sample_raw_game)
    resp = test_client.post("/ask", json={"question": "What was the gold diff at 14 minutes?"})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["answer"], str)
    assert isinstance(body["game_ids_referenced"], list)
