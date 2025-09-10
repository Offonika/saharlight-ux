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
    return {"Authorization": f"tg {build_init_data()}"}


def setup_db(monkeypatch: pytest.MonkeyPatch) -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)

    original_run_db = db.run_db

    async def run_db_wrapper(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        kwargs["sessionmaker"] = SessionLocal
        return await original_run_db(fn, *args, **kwargs)

    monkeypatch.setattr(server, "run_db", run_db_wrapper)
    import services.api.app.routers.profile as profile_router

    monkeypatch.setattr(profile_router.db_module, "run_db", run_db_wrapper)
    monkeypatch.setattr(db, "SessionLocal", SessionLocal, raising=False)
    return SessionLocal


def test_profile_get_requires_onboarding(
    monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    SessionLocal = setup_db(monkeypatch)
    with SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id="t", onboarding_complete=False))
        session.add(db.Profile(telegram_id=1))
        session.commit()
    with TestClient(server.app) as client:
        resp = client.get("/api/profile", headers=auth_headers)
        assert resp.status_code == 422

        payload = {
            "telegramId": 1,
            "icr": 1.0,
            "cf": 1.0,
            "target": 5.0,
            "low": 4.0,
            "high": 6.0,
        }
        post_resp = client.post("/api/profile", json=payload, headers=auth_headers)
        assert post_resp.status_code == 200

        resp_ok = client.get("/api/profile", headers=auth_headers)
        assert resp_ok.status_code == 200
        assert resp_ok.json()["icr"] == 1.0

    with SessionLocal() as session:
        user = session.get(db.User, 1)
        assert user is not None and user.onboarding_complete is True
