import json
import time
import hmac
import hashlib
import urllib.parse
from typing import Any, Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import services.api.app.main as server
from services.api.app.config import settings
from services.api.app.diabetes.services import db
from services.api.app.telegram_auth import TG_INIT_DATA_HEADER

TOKEN = "test-token"


def build_init_data(user_id: int = 1) -> str:
    user = json.dumps({"id": user_id, "first_name": "A"}, separators=(",", ":"))
    params = {"auth_date": str(int(time.time())), "query_id": "abc", "user": user}
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(params)


@pytest.fixture
def auth_headers(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    return {TG_INIT_DATA_HEADER: build_init_data()}


def setup_db(monkeypatch: pytest.MonkeyPatch) -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)

    async def run_db_wrapper(
        fn: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        return await db.run_db(fn, *args, sessionmaker=SessionLocal, **kwargs)

    monkeypatch.setattr(server, "run_db", run_db_wrapper)
    monkeypatch.setattr(db, "SessionLocal", SessionLocal, raising=False)
    return SessionLocal


def test_profile_post_saves_profile(
    monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    SessionLocal = setup_db(monkeypatch)
    with SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id="t"))
        session.commit()
    payload = {
        "telegramId": 1,
        "icr": 1.0,
        "cf": 1.0,
        "target": 5.0,
        "low": 4.0,
        "high": 6.0,
        "therapyType": "insulin",
    }
    with TestClient(server.app) as client:
        resp = client.post("/api/profile", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    with SessionLocal() as session:
        prof = session.get(db.Profile, 1)
        assert prof is not None
        assert prof.icr == 1.0
        assert prof.cf == 1.0
        assert prof.target_bg == 5.0
        assert prof.low_threshold == 4.0
        assert prof.high_threshold == 6.0


def test_profile_post_invalid_icr_returns_422(
    monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    SessionLocal = setup_db(monkeypatch)
    with SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id="t"))
        session.commit()
    payload = {
        "telegramId": 1,
        "icr": 0,
        "cf": 1.0,
        "target": 5.0,
        "low": 4.0,
        "high": 6.0,
        "therapyType": "insulin",
    }
    with TestClient(server.app) as client:
        resp = client.post("/api/profile", json=payload, headers=auth_headers)
    assert resp.status_code == 422
    assert resp.json() == {"detail": "icr must be greater than 0"}


def test_profile_post_user_missing_returns_404(
    monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    setup_db(monkeypatch)
    payload = {
        "telegramId": 1,
        "icr": 1.0,
        "cf": 1.0,
        "target": 5.0,
        "low": 4.0,
        "high": 6.0,
        "therapyType": "insulin",
    }
    with TestClient(server.app) as client:
        resp = client.post("/api/profile", json=payload, headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json() == {"detail": "user not found"}
