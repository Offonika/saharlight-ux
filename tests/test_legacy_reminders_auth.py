import hashlib
import hmac
import json
import logging
import time
import urllib.parse
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import services.api.app.main as server
from services.api.app.config import settings
from services.api.app.diabetes.services.db import Base, User
from services.api.app.services import reminders
from services.api.app.routers import reminders as reminders_router

TOKEN = "test-token"


def build_init_data(token: str = TOKEN, user_id: int = 1) -> str:
    user = json.dumps({"id": user_id, "first_name": "A"}, separators=(",", ":"))
    params = {
        "auth_date": str(int(time.time())),
        "query_id": "abc",
        "user": user,
    }
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(params)


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    monkeypatch.setattr(reminders, "SessionLocal", TestSession)

    async def _noop(action: str, rid: int) -> None:  # pragma: no cover - simple stub
        return None

    monkeypatch.setattr(reminders_router, "_post_job_queue_event", _noop)
    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()
    try:
        with TestClient(server.app) as test_client:
            test_client.app.dependency_overrides.clear()
            try:
                yield test_client
            finally:
                test_client.app.dependency_overrides.clear()
    finally:
        engine.dispose()


def test_post_and_get_reminders_with_auth(client: TestClient) -> None:
    init_data = build_init_data()
    resp_post = client.post(
        "/api/reminders",
        json={"telegramId": 1, "type": "sugar"},
        headers={"X-Telegram-Init-Data": init_data},
    )
    assert resp_post.status_code == 200
    reminder_id = resp_post.json()["id"]

    resp_get = client.get(
        "/api/reminders",
        params={"telegramId": 1},
        headers={"X-Telegram-Init-Data": init_data},
    )
    assert resp_get.status_code == 200
    assert any(r["id"] == reminder_id for r in resp_get.json())


def test_reminders_missing_auth(client: TestClient) -> None:
    resp = client.get("/api/reminders", params={"telegramId": 1})
    assert resp.status_code == 401


def test_reminders_matching_id(client: TestClient) -> None:
    init_data = build_init_data()
    resp = client.get(
        "/api/reminders",
        params={"telegramId": 1},
        headers={"X-Telegram-Init-Data": init_data},
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_reminders_mismatched_id(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    init_data = build_init_data()
    request_id = "req-1"
    with caplog.at_level(logging.WARNING, logger="services.api.app.routers.reminders"):
        resp = client.get(
            "/api/reminders",
            params={"telegramId": 2},
            headers={
                "X-Telegram-Init-Data": init_data,
                "X-Request-ID": request_id,
            },
        )
    assert resp.status_code == 404
    assert resp.json() == {"detail": "reminder not found"}
    assert (
        f"request_id={request_id} telegramId=2 does not match user_id=1" in caplog.text
    )


def test_reminders_invalid_telegram_id(client: TestClient) -> None:
    init_data = build_init_data(user_id=999)
    resp = client.get(
        "/api/reminders",
        params={"telegramId": 999},
        headers={"X-Telegram-Init-Data": init_data},
    )
    assert resp.status_code == 200
    assert resp.json() == []
