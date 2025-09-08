from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from services.api.app import reminder_events
from services.api.app.config import settings
from services.api.app.routers.internal_reminders import router


def test_saved_notifies(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[int] = []

    async def fake_notify(rid: int) -> None:
        called.append(rid)

    monkeypatch.setattr(settings, "internal_api_key", "token")
    monkeypatch.setattr(reminder_events, "notify_reminder_saved", fake_notify)
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        resp = client.post(
            "/internal/reminders/saved",
            json={"id": 1},
            headers={"X-Internal-API-Key": "token"},
        )
    assert resp.status_code == 200
    assert called == [1]


def test_deleted_notifies(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[int] = []

    def fake_notify(rid: int) -> None:
        called.append(rid)

    monkeypatch.setattr(settings, "internal_api_key", "token")
    monkeypatch.setattr(reminder_events, "notify_reminder_deleted", fake_notify)
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        resp = client.post(
            "/internal/reminders/deleted",
            json={"id": 2},
            headers={"X-Internal-API-Key": "token"},
        )
    assert resp.status_code == 200
    assert called == [2]


@pytest.mark.parametrize("path", ["/internal/reminders/saved", "/internal/reminders/deleted"])
def test_requires_token(monkeypatch: pytest.MonkeyPatch, path: str) -> None:
    monkeypatch.setattr(settings, "internal_api_key", "token")
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        resp = client.post(path, json={"id": 1})
        assert resp.status_code == 401
        resp = client.post(path, json={"id": 1}, headers={"X-Internal-API-Key": "wrong"})
        assert resp.status_code == 401
