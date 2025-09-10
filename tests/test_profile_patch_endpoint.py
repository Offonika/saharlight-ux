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


def setup_db(
    monkeypatch: pytest.MonkeyPatch,
    *,
    add_user: bool = True,
    onboarding_complete: bool = True,
) -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)

    if add_user:
        with SessionLocal() as session:
            session.add(
                db.User(
                    telegram_id=1,
                    thread_id="t",
                    onboarding_complete=onboarding_complete,
                )
            )
            session.commit()

    async def run_db_wrapper(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
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


def test_profile_patch_ignores_device_tz(
    monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    SessionLocal = setup_db(monkeypatch)
    with TestClient(server.app) as client:
        resp = client.patch(
            "/api/profile",
            params={"deviceTz": "Europe/Moscow"},
            json={"timezone": "Asia/Tbilisi", "timezoneAuto": True},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["timezone"] == "Asia/Tbilisi"
        assert data["timezoneAuto"] is True

    with SessionLocal() as session:
        prof = session.get(db.Profile, 1)
        assert prof is not None
        assert prof.timezone == "Asia/Tbilisi"
        assert prof.timezone_auto is True


def test_profile_patch_partial_update(
    monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    SessionLocal = setup_db(monkeypatch)
    with TestClient(server.app) as client:
        resp = client.patch("/api/profile", json={"dia": 5}, headers=auth_headers)
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


def test_profile_patch_saves_additional_fields(
    monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    SessionLocal = setup_db(monkeypatch)
    with TestClient(server.app) as client:
        resp = client.patch(
            "/api/profile",
            json={
                "rapidInsulinType": "lispro",
                "maxBolus": 12,
                "preBolus": 10,
                "afterMealMinutes": 90,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["rapidInsulinType"] == "lispro"
        assert data["maxBolus"] == 12
        assert data["preBolus"] == 10
        assert data["afterMealMinutes"] == 90

    with SessionLocal() as session:
        prof = session.get(db.Profile, 1)
        assert prof is not None
        assert prof.insulin_type == "lispro"
        assert prof.max_bolus == 12
        assert prof.prebolus_min == 10
        assert prof.postmeal_check_min == 90


def test_profile_get_returns_updated_values(
    monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    SessionLocal = setup_db(monkeypatch)
    with TestClient(server.app) as client:
        resp = client.patch(
            "/api/profile",
            json={"timezone": "Europe/Moscow", "timezoneAuto": True},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        resp = client.get("/api/profile", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["timezone"] == "Europe/Moscow"
        assert data["timezoneAuto"] is True

    with SessionLocal() as session:
        prof = session.get(db.Profile, 1)
        assert prof is not None
        assert prof.timezone == "Europe/Moscow"


def test_profile_get_returns_saved_settings(
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

        resp = client.get("/api/profile", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["timezone"] == "Europe/Moscow"
        assert data["timezoneAuto"] is True
        assert data["dia"] == 6
        assert data["roundStep"] == 1
        assert data["carbUnits"] == "xe"

    with SessionLocal() as session:
        prof = session.get(db.Profile, 1)
        assert prof is not None
        assert prof.timezone == "Europe/Moscow"
        assert prof.dia == 6
        assert prof.round_step == 1
        assert prof.carb_units == "xe"


def test_profile_patch_returns_full_profile(
    monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    SessionLocal = setup_db(monkeypatch)
    with TestClient(server.app) as client:
        resp = client.patch(
            "/api/profile",
            json={"icr": 8, "cf": 3, "target": 6, "low": 4, "high": 9},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["icr"] == 8
        assert data["cf"] == 3
        assert data["target"] == 6
        assert data["low"] == 4
        assert data["high"] == 9

        resp = client.get("/api/profile", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["icr"] == 8
        assert data["cf"] == 3
        assert data["target"] == 6
        assert data["low"] == 4
        assert data["high"] == 9

    with SessionLocal() as session:
        prof = session.get(db.Profile, 1)
        assert prof is not None
        assert prof.icr == 8
        assert prof.cf == 3
        assert prof.target_bg == 6
        assert prof.low_threshold == 4
        assert prof.high_threshold == 9


def test_profile_patch_creates_user_and_completes_onboarding(
    monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    SessionLocal = setup_db(monkeypatch, add_user=False)
    with TestClient(server.app) as client:
        resp = client.patch(
            "/api/profile",
            json={"timezone": "UTC"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    with SessionLocal() as session:
        user = session.get(db.User, 1)
        assert user is not None
        assert user.thread_id == "api"
        assert user.onboarding_complete is True
        profile = session.get(db.Profile, 1)
        assert profile is not None
        assert profile.timezone == "UTC"


def test_profile_patch_marks_existing_onboarding_complete(
    monkeypatch: pytest.MonkeyPatch, auth_headers: dict[str, str]
) -> None:
    SessionLocal = setup_db(monkeypatch, onboarding_complete=False)
    with TestClient(server.app) as client:
        resp = client.patch(
            "/api/profile",
            json={"timezone": "UTC"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    with SessionLocal() as session:
        user = session.get(db.User, 1)
        assert user is not None
        assert user.onboarding_complete is True
