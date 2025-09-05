from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.services.db import Base, User
from services.api.app.routers import onboarding as onboarding_router
from services.api.app.services import onboarding_state
from services.api.app.services.onboarding_events import OnboardingEvent
from services.api.app.telegram_auth import require_tg_user
from services.api.app.main import app


_PROFILE, _TIMEZONE, REMINDERS = range(3)


def setup_db() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            onboarding_state.OnboardingState.__table__,
            OnboardingEvent.__table__,
        ],
    )
    return sessionmaker(bind=engine, class_=Session)


def make_client(monkeypatch: pytest.MonkeyPatch, session_local: sessionmaker[Session]) -> TestClient:
    async def run_db(fn, *args, sessionmaker: sessionmaker[Session] = session_local, **kwargs):
        with sessionmaker() as session:
            return fn(session, *args, **kwargs)

    monkeypatch.setattr(onboarding_router, "run_db", run_db, raising=False)
    monkeypatch.setattr(onboarding_router, "SessionLocal", session_local, raising=False)
    monkeypatch.setattr(onboarding_state, "run_db", run_db, raising=False)
    monkeypatch.setattr(onboarding_state, "SessionLocal", session_local, raising=False)

    app.dependency_overrides[require_tg_user] = lambda: {"id": 1}
    return TestClient(app)


def teardown_client() -> None:
    app.dependency_overrides.clear()


def add_user(session_local: sessionmaker[Session]) -> None:
    with session_local() as session:
        session.add(User(telegram_id=1, thread_id="webapp"))
        session.commit()


def test_post_event_persists(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    add_user(session_local)
    client = make_client(monkeypatch, session_local)
    with client:
        resp = client.post("/api/onboarding/events", json={"event": "onboarding_started"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    with session_local() as session:
        ev = session.query(OnboardingEvent).one()
        assert ev.event_name == "onboarding_started"
        assert ev.user_id == 1
    teardown_client()


def test_status_initial(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    add_user(session_local)
    client = make_client(monkeypatch, session_local)
    with client:
        resp = client.get("/api/onboarding/status")
    assert resp.status_code == 200
    assert resp.json() == {
        "completed": False,
        "step": "profile",
        "missing": ["profile", "reminders"],
    }
    teardown_client()


def test_status_reminders_step(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    with session_local() as session:
        session.add(User(telegram_id=1, thread_id="webapp"))
        session.add(
            onboarding_state.OnboardingState(user_id=1, step=REMINDERS, data={}, variant=None)
        )
        session.commit()
    client = make_client(monkeypatch, session_local)
    with client:
        resp = client.get("/api/onboarding/status")
    assert resp.status_code == 200
    assert resp.json() == {"completed": False, "step": "reminders", "missing": ["reminders"]}
    teardown_client()


def test_status_completed(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    with session_local() as session:
        session.add(User(telegram_id=1, thread_id="webapp"))
        session.add(
            onboarding_state.OnboardingState(
                user_id=1,
                step=REMINDERS,
                data={},
                variant=None,
                completed_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
    client = make_client(monkeypatch, session_local)
    with client:
        resp = client.get("/api/onboarding/status")
    assert resp.status_code == 200
    assert resp.json() == {"completed": True, "step": None, "missing": []}
    teardown_client()
