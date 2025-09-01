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

    async def run_db_wrapper(
        fn: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        return await db.run_db(fn, *args, sessionmaker=SessionLocal, **kwargs)

    monkeypatch.setattr(server, "run_db", run_db_wrapper)
    return SessionLocal


def test_profile_patch_returns_status_ok(
    monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    SessionLocal = setup_db(monkeypatch)
    with TestClient(server.app) as client:
        resp = client.patch(
            "/api/profile",
            json={
                "timezone": "Europe/Moscow",
                "timezoneAuto": True,
                "quietStart": "22:30",
                "quietEnd": "06:15",
                "sosContact": "+123",
                "sosAlertsEnabled": False,
            },
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

    with SessionLocal() as session:
        user = session.get(db.User, 1)
        profile = session.get(db.Profile, 1)
        assert user is not None
        assert profile is not None
        assert user.timezone == "Europe/Moscow"
        assert user.timezone_auto is True
        assert profile.quiet_start.strftime("%H:%M:%S") == "22:30:00"
        assert profile.quiet_end.strftime("%H:%M:%S") == "06:15:00"
        assert profile.sos_contact == "+123"
        assert profile.sos_alerts_enabled is False
