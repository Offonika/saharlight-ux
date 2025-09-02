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
    monkeypatch.setattr(db, "SessionLocal", SessionLocal, raising=False)
    return SessionLocal


def test_profile_patch_returns_settings(
    monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    SessionLocal = setup_db(monkeypatch)
    with TestClient(server.app) as client:
        resp = client.patch(
            "/api/profile",
            json={
                "timezone": "Europe/Moscow",
                "timezoneAuto": True,
                "dia": 6,
                "roundStep": 1,
                "carbUnits": "xe",
            },
            headers=auth_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["timezone"] == "Europe/Moscow"
    assert data["timezoneAuto"] is True
    assert data["dia"] == 6
    assert data["roundStep"] == 1
    assert data["carbUnits"] == "xe"
    assert data["sosAlertsEnabled"] is True
    assert data["sosContact"] is None

    with SessionLocal() as session:
        prof = session.get(db.Profile, 1)
        assert prof is not None
        assert prof.timezone == "Europe/Moscow"
        assert prof.timezone_auto is True
        assert prof.dia == 6
        assert prof.round_step == 1
        assert prof.carb_units == "xe"
        assert prof.sos_alerts_enabled is True
        assert prof.sos_contact is None


def test_profile_patch_partial_update(
    monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    SessionLocal = setup_db(monkeypatch)
    with TestClient(server.app) as client:
        resp = client.patch(
            "/api/profile", json={"dia": 5}, headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["dia"] == 5
        assert data["roundStep"] == 0.5
        assert data["carbUnits"] == "g"
        assert data["sosAlertsEnabled"] is True
        assert data["sosContact"] is None

    with SessionLocal() as session:
        prof = session.get(db.Profile, 1)
        assert prof is not None
        assert prof.dia == 5
        assert prof.round_step == 0.5
        assert prof.carb_units == "g"
        assert prof.sos_alerts_enabled is True
        assert prof.sos_contact is None


def test_profile_patch_sets_grams_per_xe(
    monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    SessionLocal = setup_db(monkeypatch)
    with TestClient(server.app) as client:
        resp = client.patch(
            "/api/profile", json={"gramsPerXe": 15}, headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["gramsPerXe"] == 15

    with SessionLocal() as session:
        prof = session.get(db.Profile, 1)
        assert prof is not None
        assert prof.grams_per_xe == 15
