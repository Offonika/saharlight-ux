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


def setup_db(monkeypatch: pytest.MonkeyPatch) -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)

    # Ensure application code uses the in-memory sessionmaker
    monkeypatch.setattr(db, "SessionLocal", SessionLocal)

    async def run_db_wrapper(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return await db.run_db(fn, *args, sessionmaker=SessionLocal, **kwargs)

    monkeypatch.setattr(server, "run_db", run_db_wrapper)
    return SessionLocal


TOKEN = "test-token"


def build_init_data(user_id: int = 1) -> str:
    user = json.dumps({"id": user_id, "first_name": "A"}, separators=(",", ":"))
    params = {"auth_date": str(int(time.time())), "query_id": "abc", "user": user}
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    params["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(params)


def test_create_user_authorized(monkeypatch: pytest.MonkeyPatch) -> None:
    Session = setup_db(monkeypatch)
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    init_data = build_init_data(42)
    with TestClient(server.app) as client:
        resp = client.post(
            "/api/user",
            json={"telegramId": 42},
            headers={TG_INIT_DATA_HEADER: init_data},
        )
    assert resp.status_code == 200

    with Session() as session:
        user = session.get(db.User, 42)
        assert user is not None
        assert user.thread_id == "webapp"


def test_create_users_authorized(monkeypatch: pytest.MonkeyPatch) -> None:
    Session = setup_db(monkeypatch)
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    init_data = build_init_data(99)
    with TestClient(server.app) as client:
        resp = client.post(
            "/api/users",
            json={"telegramId": 99},
            headers={TG_INIT_DATA_HEADER: init_data},
        )
    assert resp.status_code == 200

    with Session() as session:
        user = session.get(db.User, 99)
        assert user is not None
        assert user.thread_id == "webapp"


def test_create_user_unauthorized(monkeypatch: pytest.MonkeyPatch) -> None:
    setup_db(monkeypatch)
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    init_data = build_init_data(1)
    with TestClient(server.app) as client:
        resp = client.post(
            "/api/user",
            json={"telegramId": 42},
            headers={TG_INIT_DATA_HEADER: init_data},
        )
    assert resp.status_code == 403
