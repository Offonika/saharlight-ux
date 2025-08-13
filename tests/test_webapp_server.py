"""Tests for minimal FastAPI webapp."""

from fastapi.testclient import TestClient

import services.api.app.main as server

client = TestClient(server.app)


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_static_ui_serving() -> None:
    resp = client.get("/ui")
    assert resp.status_code == 200
    assert "<html" in resp.text.lower()


def test_unknown_ui_route_serves_index() -> None:
    resp = client.get("/ui/reminders")
    assert resp.status_code == 200
    assert "<html" in resp.text.lower()
