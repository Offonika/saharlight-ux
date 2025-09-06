from __future__ import annotations

from typing import Callable, TypeVar

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.services.db import (
    Base,
    Profile,
    Reminder,
    ReminderType,
    ScheduleKind,
    User,
)
from services.api.app.models.onboarding_event import OnboardingEvent
from services.api.app.routers import onboarding
from services.api.app.telegram_auth import check_token

T = TypeVar("T")


def setup_db() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def patch_db(monkeypatch: pytest.MonkeyPatch, session_local: sessionmaker[Session]) -> None:
    async def run_db(
        fn: Callable[[Session], T],
        *args: object,
        sessionmaker: sessionmaker[Session] = session_local,
        **kwargs: object,
    ) -> T:
        with sessionmaker() as session:
            return fn(session, *args, **kwargs)

    monkeypatch.setattr(onboarding, "SessionLocal", session_local, raising=False)
    monkeypatch.setattr(onboarding, "run_db", run_db, raising=False)


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    session_local = setup_db()
    patch_db(monkeypatch, session_local)

    from services.api.app.main import app

    app.dependency_overrides[check_token] = lambda: {"id": 1}
    return TestClient(app)


def test_post_event_records(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    resp = client.post("/api/onboarding/events", json={"event": "start", "step": 1})
    assert resp.status_code == 200

    SessionLocal = onboarding.SessionLocal
    with SessionLocal() as session:
        ev = session.query(OnboardingEvent).one()
        assert ev.user_id == 1
        assert ev.event == "start"
        assert ev.step == "1"


def test_status_variants(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    SessionLocal = onboarding.SessionLocal
    # insert user and profile/reminder combinations
    with SessionLocal() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    # no profile -> expect profile step
    resp = client.get("/api/onboarding/status")
    assert resp.status_code == 200
    assert resp.json() == {
        "completed": False,
        "step": "profile",
        "missing": ["profile", "reminders"],
    }

    # add profile
    with SessionLocal() as session:
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
        session.commit()

    resp = client.get("/api/onboarding/status")
    assert resp.status_code == 200
    assert resp.json() == {
        "completed": False,
        "step": "reminders",
        "missing": ["reminders"],
    }

    # add reminder
    with SessionLocal() as session:
        session.add(
            Reminder(
                telegram_id=1,
                type=ReminderType.custom,
                kind=ScheduleKind.every,
                interval_minutes=60,
            )
        )
        session.commit()

    resp = client.get("/api/onboarding/status")
    assert resp.status_code == 200
    assert resp.json() == {"completed": True, "step": None, "missing": []}

    with SessionLocal() as session:
        events = session.query(OnboardingEvent).filter_by(event="onboarding_completed").all()
        assert len(events) == 1
        assert events[0].step == str(onboarding.REMINDERS)
