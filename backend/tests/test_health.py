"""
Phase 1 smoke tests.

Only the /health endpoint is expected to work. All business routes
return 501 and are not tested here (Phase 2 responsibility).
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import app


def test_health_returns_200() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_status_ok() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.json() == {"status": "ok"}
