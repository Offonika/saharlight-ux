from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import services.api.app.routers.onboarding as onboarding_router
import services.api.app.services.onboarding_events as onboarding_events
from services.api.app.diabetes.services.db import Base, Profile, Reminder, User
from services.api.app.models.onboarding_event import OnboardingEvent
from services.api.app.telegram_auth import check_token
from services.api.app.main import app


def setup_db() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[User.__table__, Profile.__table__, Reminder.__table__, OnboardingEvent.__table__],
    )
    return sessionmaker(bind=engine, class_=Session)


def make_client(monkeypatch: pytest.MonkeyPatch, session_local: sessionmaker[Session]) -> TestClient:
    async def run_db(fn, *args, sessionmaker: sessionmaker[Session] = session_local, **kwargs):
        with sessionmaker() as session:
            return fn(session, *args, **kwargs)

    monkeypatch.setattr(onboarding_router, "run_db", run_db, raising=False)
    monkeypatch.setattr(onboarding_router, "SessionLocal", session_local, raising=False)
    monkeypatch.setattr(onboarding_events, "run_db", run_db, raising=False)
    monkeypatch.setattr(onboarding_events, "SessionLocal", session_local, raising=False)

    app.dependency_overrides[check_token] = lambda: {"id": 1}
    return TestClient(app)


def teardown_client() -> None:
    app.dependency_overrides.clear()


def add_user(session_local: sessionmaker[Session]) -> None:
    with session_local() as session:
        session.add(User(telegram_id=1, thread_id="webapp"))
        session.commit()


def add_profile(session_local: sessionmaker[Session]) -> None:
    with session_local() as session:
        session.add(
            Profile(
                telegram_id=1,
                icr=1.0,
                cf=1.0,
                target_bg=5.5,
                low_threshold=4.0,
                high_threshold=8.0,
                timezone="UTC",
            )
        )
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
        assert ev.event == "onboarding_started"
        assert ev.user_id == 1
    teardown_client()


def test_post_event_with_variant(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    add_user(session_local)
    client = make_client(monkeypatch, session_local)
    with client:
        resp = client.post(
            "/api/onboarding/events",
            json={"event": "onboarding_started", "meta": {"variant": "B"}},
        )
    assert resp.status_code == 200
    with session_local() as session:
        ev = session.query(OnboardingEvent).one()
        assert ev.variant == "B"
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
    add_user(session_local)
    add_profile(session_local)
    client = make_client(monkeypatch, session_local)
    with client:
        resp = client.get("/api/onboarding/status")
    assert resp.status_code == 200
    assert resp.json() == {"completed": False, "step": "reminders", "missing": ["reminders"]}
    teardown_client()


def test_status_completed_with_reminder(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    add_user(session_local)
    add_profile(session_local)
    with session_local() as session:
        session.add(Reminder(telegram_id=1, type="sugar", title="t"))
        session.commit()
    client = make_client(monkeypatch, session_local)
    with client:
        resp = client.get("/api/onboarding/status")
    assert resp.status_code == 200
    assert resp.json() == {"completed": True, "step": None, "missing": []}
    with session_local() as session:
        ev = session.query(OnboardingEvent).filter_by(event="onboarding_completed").one()
        assert ev.user_id == 1
    teardown_client()


def test_status_skipped_reminders(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    add_user(session_local)
    add_profile(session_local)
    with session_local() as session:
        session.add(
            OnboardingEvent(
                user_id=1,
                event="onboarding_completed",
                meta_json={"skippedReminders": True},
                ts=datetime.now(timezone.utc),
            )
        )
        session.commit()
    client = make_client(monkeypatch, session_local)
    with client:
        resp = client.get("/api/onboarding/status")
    assert resp.status_code == 200
    assert resp.json() == {"completed": True, "step": None, "missing": []}
    teardown_client()
