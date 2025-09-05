from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.services.db import Base
from services.api.app.services import onboarding_state
from services.api.app.services.onboarding_events import (
    OnboardingEvent,
    PROFILE,
    TIMEZONE,
)
import services.api.app.services.onboarding_events as onboarding_events


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, sessionmaker[SASession]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, class_=SASession)
    Base.metadata.create_all(
        engine,
        tables=[OnboardingEvent.__table__, onboarding_state.OnboardingState.__table__],
    )

    async def run_db(fn, *args, sessionmaker: sessionmaker[SASession] = SessionLocal, **kwargs):
        with sessionmaker() as session:
            return fn(session, *args, **kwargs)

    monkeypatch.setattr(onboarding_events, "SessionLocal", SessionLocal, raising=False)
    monkeypatch.setattr(onboarding_events, "run_db", run_db, raising=False)
    monkeypatch.setattr(onboarding_state, "SessionLocal", SessionLocal, raising=False)
    monkeypatch.setattr(onboarding_state, "run_db", run_db, raising=False)

    from services.api.app.telegram_auth import require_tg_user as real_require
    from services.api.app.main import app

    app.dependency_overrides[real_require] = lambda: {"id": 1}

    client = TestClient(app)
    yield client, SessionLocal
    client.close()
    app.dependency_overrides.clear()
    engine.dispose()


def test_status_completed_event(client: tuple[TestClient, sessionmaker[SASession]]) -> None:
    client_app, SessionLocal = client
    with SessionLocal() as session:
        session.add(OnboardingEvent(user_id=1, event_name="onboarding_completed", step=2, variant=None))
        session.commit()
    resp = client_app.get("/api/onboarding/status", params={"telegramId": 1})
    assert resp.status_code == 200
    assert resp.json() == {"step": None, "missingSteps": []}


def test_status_returns_missing_steps(client: tuple[TestClient, sessionmaker[SASession]]) -> None:
    client_app, SessionLocal = client
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        session.add(
            onboarding_state.OnboardingState(
                user_id=1,
                step=TIMEZONE,
                data={},
                variant="A",
                completed_at=None,
                updated_at=now,
            )
        )
        session.commit()
    resp = client_app.get("/api/onboarding/status", params={"telegramId": 1})
    assert resp.status_code == 200
    assert resp.json() == {"step": TIMEZONE, "missingSteps": [TIMEZONE, onboarding_events.REMINDERS]}


def test_status_canceled_after_completion(client: tuple[TestClient, sessionmaker[SASession]]) -> None:
    client_app, SessionLocal = client
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        session.add_all(
            [
                OnboardingEvent(
                    user_id=1,
                    event_name="onboarding_completed",
                    step=2,
                    variant=None,
                    created_at=now - timedelta(seconds=1),
                ),
                OnboardingEvent(
                    user_id=1,
                    event_name="onboarding_canceled",
                    step=2,
                    variant=None,
                    created_at=now,
                ),
            ]
        )
        session.commit()
    resp = client_app.get("/api/onboarding/status", params={"telegramId": 1})
    assert resp.status_code == 200
    assert resp.json() == {"step": PROFILE, "missingSteps": [PROFILE, TIMEZONE, onboarding_events.REMINDERS]}


def test_status_stale_state(client: tuple[TestClient, sessionmaker[SASession]]) -> None:
    client_app, SessionLocal = client
    old = datetime.now(timezone.utc) - timedelta(days=15)
    with SessionLocal() as session:
        session.add(
            onboarding_state.OnboardingState(
                user_id=1,
                step=TIMEZONE,
                data={},
                variant=None,
                completed_at=None,
                updated_at=old,
            )
        )
        session.commit()
    resp = client_app.get("/api/onboarding/status", params={"telegramId": 1})
    assert resp.status_code == 200
    assert resp.json() == {"step": PROFILE, "missingSteps": [PROFILE, TIMEZONE, onboarding_events.REMINDERS]}
    with SessionLocal() as session:
        assert session.get(onboarding_state.OnboardingState, 1) is None
