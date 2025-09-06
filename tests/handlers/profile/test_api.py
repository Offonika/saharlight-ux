import pytest
from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker
from unittest.mock import MagicMock

import importlib

from services.api.app.diabetes.services.db import Base, User, Profile
from services.api.app import main
from fastapi import FastAPI
from fastapi.testclient import TestClient

profile_api = importlib.import_module("services.api.app.diabetes.handlers.profile.api")


@pytest.fixture()
def session_factory() -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession: sessionmaker[Session] = sessionmaker(
        bind=engine, autoflush=False, autocommit=False
    )
    try:
        yield TestSession
    finally:
        engine.dispose()


def test_post_profile_success() -> None:
    class DummyAPI:
        def __init__(self) -> None:
            self.called_with: object | None = None

        def profiles_post(self, profile: object) -> None:
            self.called_with = profile

    class DummyProfile:
        def __init__(
            self,
            telegram_id: int,
            icr: float,
            cf: float,
            target: float,
            low: float,
            high: float,
        ) -> None:
            self.telegram_id = telegram_id
            self.icr = icr
            self.cf = cf
            self.target = target
            self.low = low
            self.high = high

    api = DummyAPI()
    ok, err = profile_api.post_profile(
        api,
        Exception,
        DummyProfile,
        1,
        1.0,
        2.0,
        3.0,
        4.0,
        5.0,
    )
    assert ok is True and err is None
    assert isinstance(api.called_with, DummyProfile)
    assert api.called_with.icr == 1.0


def test_post_profile_error() -> None:
    class ApiExc(Exception):
        pass

    class DummyAPI:
        def profiles_post(self, profile: object) -> None:
            raise ApiExc("boom")

    class DummyProfile:
        def __init__(
            self,
            telegram_id: int,
            icr: float,
            cf: float,
            target: float,
            low: float,
            high: float,
        ) -> None:
            self.telegram_id = telegram_id
            self.icr = icr
            self.cf = cf
            self.target = target
            self.low = low
            self.high = high

    ok, err = profile_api.post_profile(
        DummyAPI(),
        ApiExc,
        DummyProfile,
        1,
        1.0,
        2.0,
        3.0,
        4.0,
        5.0,
    )
    assert ok is False
    assert err == "boom"


def test_save_profile_persists(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()
        ok = profile_api.save_profile(
            session,
            1,
            10.0,
            2.0,
            5.0,
            3.0,
            8.0,
            sos_contact="911",
            sos_alerts_enabled=False,
        )
        assert ok is True

    with session_factory() as session:
        prof = session.get(Profile, 1)
        assert prof is not None
        assert prof.icr == 10.0
        assert prof.cf == 2.0
        assert prof.target_bg == 5.0
        assert prof.low_threshold == 3.0
        assert prof.high_threshold == 8.0
        assert prof.sos_contact == "911"
        assert prof.sos_alerts_enabled is False


def test_save_profile_commit_failure(
    monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker[Session]
) -> None:
    def fail_commit(session: object) -> None:
        raise profile_api.CommitError

    monkeypatch.setattr(profile_api, "commit", fail_commit)
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()
        ok = profile_api.save_profile(session, 1, 1.0, 1.0, 1.0, 1.0, 1.0)
        assert ok is False

    with session_factory() as session:
        prof = session.get(Profile, 1)
        assert prof is None


def test_save_profile_creates_missing_user(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as session:
        ok = profile_api.save_profile(session, 1, 1.0, 2.0, 3.0, 4.0, 5.0)
        assert ok is True

    with session_factory() as session:
        user = session.get(User, 1)
        profile = session.get(Profile, 1)
        assert user is not None and profile is not None


def test_local_profiles_post_failure(
    monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker[Session]
) -> None:
    api = profile_api.LocalProfileAPI(session_factory)
    monkeypatch.setattr(profile_api, "save_profile", lambda *a, **k: False)
    with pytest.raises(profile_api.ProfileSaveError):
        api.profiles_post(profile_api.LocalProfile(telegram_id=1))


def test_local_profiles_roundtrip(session_factory: sessionmaker[Session]) -> None:
    api = profile_api.LocalProfileAPI(session_factory)

    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    profile = profile_api.LocalProfile(
        telegram_id=1,
        icr=1.0,
        cf=2.0,
        target=3.0,
        low=4.0,
        high=5.0,
        sos_contact="112",
        sos_alerts_enabled=False,
    )
    api.profiles_post(profile)
    fetched = api.profiles_get(1)
    assert fetched is not None
    assert fetched.sos_contact == "112"
    assert fetched.sos_alerts_enabled is False


def test_set_timezone_persists(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Profile(telegram_id=1, timezone="UTC"))
        session.commit()
        found, ok = profile_api.set_timezone(session, 1, "Europe/Moscow")
        assert (found, ok) == (True, True)

    with session_factory() as session:
        prof = session.get(Profile, 1)
        assert prof is not None
        assert prof.timezone == "Europe/Moscow"


def test_set_timezone_commit_failure(
    monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker[Session]
) -> None:
    def fail_commit(session: object) -> None:
        raise profile_api.CommitError

    monkeypatch.setattr(profile_api, "commit", fail_commit)
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Profile(telegram_id=1, timezone="UTC"))
        session.commit()
        found, ok = profile_api.set_timezone(session, 1, "Europe/Moscow")
        assert (found, ok) == (True, False)

    with session_factory() as session:
        prof = session.get(Profile, 1)
        assert prof is not None
        assert prof.timezone == "UTC"


def test_set_timezone_user_missing(
    monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker[Session]
) -> None:
    commit_mock = MagicMock(return_value=None)
    monkeypatch.setattr(profile_api, "commit", commit_mock)
    with session_factory() as session:
        existed, ok = profile_api.set_timezone(session, 999, "UTC")
        assert (existed, ok) == (False, True)
        commit_mock.assert_called_once()


def _build_app(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> FastAPI:
    app = FastAPI()
    app.include_router(main.api_router, prefix="/api")
    app.dependency_overrides[main.require_tg_user] = lambda: {"id": 1}
    import services.api.app.diabetes.services.db as db
    import services.api.app.legacy as legacy

    monkeypatch.setattr(db, "SessionLocal", session_factory, raising=False)

    async def _run_db(fn, *args, **kwargs):
        return await db.run_db(fn, *args, sessionmaker=session_factory, **kwargs)

    monkeypatch.setattr(main, "run_db", _run_db)
    monkeypatch.setattr(legacy, "run_db", _run_db)
    return app


def test_profile_patch_updates_timezone(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    app = _build_app(session_factory, monkeypatch)
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Profile(telegram_id=1, timezone="UTC", timezone_auto=True))
        session.commit()
    with TestClient(app) as client:
        resp = client.patch(
            "/api/profile",
            json={"timezone": "Europe/Moscow", "timezoneAuto": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["timezone"] == "Europe/Moscow"
        assert data["timezoneAuto"] is False
        assert data["sosAlertsEnabled"] is True
        assert data["sosContact"] is None
    with session_factory() as session:
        prof = session.get(Profile, 1)
        assert prof is not None
        assert prof.timezone == "Europe/Moscow"
        assert prof.timezone_auto is False


def test_profile_patch_auto_device_timezone(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    app = _build_app(session_factory, monkeypatch)
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Profile(telegram_id=1, timezone="UTC", timezone_auto=True))
        session.commit()
    with TestClient(app) as client:
        resp = client.patch(
            "/api/profile",
            params={"deviceTz": "Europe/Moscow"},
            json={"timezoneAuto": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["timezone"] == "Europe/Moscow"
        assert data["timezoneAuto"] is True
        assert data["sosAlertsEnabled"] is True
        assert data["sosContact"] is None
    with session_factory() as session:
        prof = session.get(Profile, 1)
        assert prof is not None
        assert prof.timezone == "Europe/Moscow"
        assert prof.timezone_auto is True


def test_profiles_get_returns_timezone(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    app = _build_app(session_factory, monkeypatch)
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(
            Profile(
                telegram_id=1,
                timezone="Europe/Moscow",
                timezone_auto=False,
                icr=1.0,
                cf=2.0,
                target_bg=5.0,
                low_threshold=4.0,
                high_threshold=6.0,
            )
        )
        session.commit()
    with TestClient(app) as client:
        resp = client.get("/api/profiles", params={"telegramId": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert data["timezone"] == "Europe/Moscow"
        assert data["timezoneAuto"] is False


def test_profiles_get_returns_settings_fields(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    app = _build_app(session_factory, monkeypatch)
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(
            Profile(
                telegram_id=1,
                timezone="UTC",
                timezone_auto=True,
                dia=5.5,
                round_step=0.1,
                carb_units="xe",
                grams_per_xe=15.0,
                therapy_type="mixed",
                glucose_units="mg/dL",
                insulin_type="aspart",
                max_bolus=8.0,
                prebolus_min=10,
                postmeal_check_min=120,
            )
        )
        session.commit()
    with TestClient(app) as client:
        resp = client.get("/api/profiles", params={"telegramId": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert data["dia"] == 5.5
        assert data["roundStep"] == 0.1
        assert data["carbUnits"] == "xe"
        assert data["gramsPerXe"] == 15.0
        assert data["therapyType"] == "mixed"
        assert data["glucoseUnits"] == "mg/dL"
        assert data["rapidInsulinType"] == "aspart"
        assert data["maxBolus"] == 8.0
        assert data["preBolus"] == 10
        assert data["afterMealMinutes"] == 120
