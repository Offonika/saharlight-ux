import hashlib
import hmac
import json
import time
import urllib.parse
from typing import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.config import settings
from services.api.app.diabetes.services.db import Base, User
import services.api.app.services.onboarding_events as onboarding_events
import services.api.app.services.onboarding_state as onboarding_state
from services.api.app.diabetes.services import db as db_module
import services.api.app.routers.onboarding as onboarding_module
from services.api.app.routers.onboarding import router as onboarding_router

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
    SessionLocal = sessionmaker(bind=engine, class_=Session)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    monkeypatch.setattr(onboarding_events, "SessionLocal", SessionLocal, raising=False)
    monkeypatch.setattr(onboarding_state, "SessionLocal", SessionLocal, raising=False)
    monkeypatch.setattr(db_module, "SessionLocal", SessionLocal, raising=False)
    monkeypatch.setattr(onboarding_module, "SessionLocal", SessionLocal, raising=False)

    async def run_db(fn, *args, sessionmaker: sessionmaker[Session] = SessionLocal, **kwargs):
        with sessionmaker() as session:
            return fn(session, *args, **kwargs)

    monkeypatch.setattr(onboarding_events, "run_db", run_db, raising=False)
    monkeypatch.setattr(onboarding_state, "run_db", run_db, raising=False)
    monkeypatch.setattr(db_module, "run_db", run_db, raising=False)
    monkeypatch.setattr(onboarding_module, "run_db", run_db, raising=False)

    with SessionLocal() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    app = FastAPI()
    app.include_router(onboarding_router, prefix="/api")

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        engine.dispose()


def test_post_event_uses_header_user(client: TestClient) -> None:
    init_data = build_init_data()
    resp = client.post(
        "/api/onboarding/events",
        json={"name": "onboarding_started", "step": 0, "variant": "A"},
        headers={"X-Telegram-Init-Data": init_data},
    )
    assert resp.status_code == 200
    with onboarding_events.SessionLocal() as session:
        ev = session.query(onboarding_events.OnboardingEvent).one()
        assert ev.user_id == 1
        assert ev.event_name == "onboarding_started"
        assert ev.step == 0
        assert ev.variant == "A"


def test_post_event_requires_auth(client: TestClient) -> None:
    resp = client.post(
        "/api/onboarding/events",
        json={"name": "onboarding_started", "step": 0},
    )
    assert resp.status_code == 401


def test_status_reflects_completion(client: TestClient) -> None:
    init_data = build_init_data()
    resp = client.get(
        "/api/onboarding/status",
        headers={"X-Telegram-Init-Data": init_data},
    )
    data = resp.json()
    assert resp.status_code == 200
    assert data["completed"] is False
    assert data["step"] == 0

    import asyncio

    asyncio.run(onboarding_state.save_state(1, 1, {}))
    resp2 = client.get(
        "/api/onboarding/status",
        headers={"X-Telegram-Init-Data": init_data},
    )
    data2 = resp2.json()
    assert data2["completed"] is False
    assert data2["step"] == 1

    asyncio.run(onboarding_state.complete_state(1))
    resp3 = client.get(
        "/api/onboarding/status",
        headers={"X-Telegram-Init-Data": init_data},
    )
    data3 = resp3.json()
    assert data3["completed"] is True
