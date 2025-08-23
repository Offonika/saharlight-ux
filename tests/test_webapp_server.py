from fastapi.testclient import TestClient
import pytest

import services.api.app.main as server


@pytest.mark.parametrize("prefix", ("", "/api"))
def test_health(prefix: str) -> None:
    with TestClient(server.app) as client:
        resp = client.get(f"{prefix}/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


def test_static_ui_serving() -> None:
    with TestClient(server.app) as client:
        resp = client.get("/ui")
        assert resp.status_code == 200
        assert "<html" in resp.text.lower()


def test_unknown_ui_route_serves_index() -> None:
    with TestClient(server.app) as client:
        resp = client.get("/ui/reminders")
        assert resp.status_code == 200
        assert "<html" in resp.text.lower()
