from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.config import settings
from services.api.app.diabetes.services.db import Base, Profile, Reminder, User
from services.api.app.diabetes.schemas.reminders import ReminderType, ScheduleKind
from services.api.app.main import app
from services.api.app.routers import onboarding as onboarding_router
from services.api.app.services import onboarding_state
from services.api.app.services.onboarding_events import OnboardingEvent
from services.api.app.telegram_auth import TG_INIT_DATA_HEADER
from tests.test_telegram_auth import TOKEN, build_init_data


setattr(OnboardingEvent, "event_name", OnboardingEvent.event)


# Helpers ---------------------------------------------------------------------

def setup_db() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            onboarding_state.OnboardingState.__table__,
            OnboardingEvent.__table__,
            Profile.__table__,
            Reminder.__table__,
        ],
    )
    return sessionmaker(bind=engine, class_=Session)


def make_client(
    monkeypatch: pytest.MonkeyPatch, session_local: sessionmaker[Session]
) -> TestClient:
    async def run_db(
        fn, *args, sessionmaker: sessionmaker[Session] = session_local, **kwargs
    ):
        with sessionmaker() as session:
            return fn(session, *args, **kwargs)

    monkeypatch.setattr(onboarding_router, "run_db", run_db, raising=False)
    monkeypatch.setattr(onboarding_router, "SessionLocal", session_local, raising=False)
    monkeypatch.setattr(onboarding_state, "run_db", run_db, raising=False)
    monkeypatch.setattr(onboarding_state, "SessionLocal", session_local, raising=False)
    app.dependency_overrides.clear()
    return TestClient(app)


def add_user(session_local: sessionmaker[Session], user_id: int) -> None:
    with session_local() as session:
        session.add(User(telegram_id=user_id, thread_id="webapp"))
        session.commit()


# Tests -----------------------------------------------------------------------

def test_post_event_header_user(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    add_user(session_local, user_id=42)
    client = make_client(monkeypatch, session_local)
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    headers = {TG_INIT_DATA_HEADER: build_init_data(user_id=42)}
    with client:
        resp = client.post(
            "/api/onboarding/events", json={"event": "onboarding_started"}, headers=headers
        )
    assert resp.status_code == 200
    with session_local() as session:
        ev = session.query(OnboardingEvent).one()
        assert ev.user_id == 42
        assert ev.event == "onboarding_started"


def test_status_incomplete(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    add_user(session_local, user_id=1)
    client = make_client(monkeypatch, session_local)
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    headers = {TG_INIT_DATA_HEADER: build_init_data(user_id=1)}
    with client:
        resp = client.get("/api/onboarding/status", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {
        "completed": False,
        "step": "profile",
        "missing": ["profile", "reminders"],
    }


def test_status_completed(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    with session_local() as session:
        session.add(User(telegram_id=1, thread_id="webapp"))
        session.add(
            onboarding_state.OnboardingState(
                user_id=1,
                step=0,
                data={},
                variant=None,
                completed_at=datetime.now(timezone.utc),
            )
        )
        session.add(
            Profile(
                telegram_id=1,
                icr=1,
                cf=1,
                target_bg=5.5,
                low_threshold=4.0,
                high_threshold=8.0,
                timezone="UTC",
            )
        )
        session.add(
            Reminder(
                telegram_id=1,
                type=ReminderType.custom,
                kind=ScheduleKind.every,
                interval_minutes=60,
            )
        )
        session.commit()
    client = make_client(monkeypatch, session_local)
    monkeypatch.setattr(settings, "telegram_token", TOKEN)
    headers = {TG_INIT_DATA_HEADER: build_init_data(user_id=1)}
    with client:
        resp = client.get("/api/onboarding/status", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"completed": True, "step": None, "missing": []}
