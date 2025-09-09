import hashlib
import hmac
import json
import time
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

    async def run_db_wrapper(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return await db.run_db(fn, *args, sessionmaker=SessionLocal, **kwargs)

    monkeypatch.setattr(server, "run_db", run_db_wrapper)
    monkeypatch.setattr(db, "SessionLocal", SessionLocal, raising=False)
    return SessionLocal


def test_post_users_creates_record(
    monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    SessionLocal = setup_db(monkeypatch)
    with TestClient(server.app) as client:
        resp = client.post("/api/users", json={"telegramId": 1}, headers=auth_headers)
    assert resp.status_code == 200
    with SessionLocal() as session:
        user = session.get(db.User, 1)
        assert user is not None
        assert user.thread_id == "webapp"
