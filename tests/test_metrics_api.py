from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, TypeVar

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Column, MetaData, String, Table, TIMESTAMP, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.routers import metrics


def setup_db() -> tuple[sessionmaker[Session], datetime]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata = MetaData()
    events = Table(
        "onboarding_events",
        metadata,
        Column("variant", String),
        Column("step", String),
        Column("created_at", TIMESTAMP(timezone=True)),
    )
    metadata.create_all(engine)
    session_local = sessionmaker(bind=engine)
    now = datetime.now()
    with engine.begin() as conn:
        conn.execute(
            events.insert(),
            [
                {"variant": "A", "step": "start", "created_at": now},
                {"variant": "A", "step": "step1", "created_at": now},
                {"variant": "A", "step": "finish", "created_at": now},
                {"variant": "B", "step": "start", "created_at": now},
            ],
        )
    return session_local, now


T = TypeVar("T")


def test_onboarding_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local, now = setup_db()

    async def run_db(
        fn: Callable[[Session], T],
        *args: object,
        sessionmaker: sessionmaker[Session] = session_local,
        **kwargs: object,
    ) -> T:
        with sessionmaker() as session:
            return fn(session)

    monkeypatch.setattr(metrics, "SessionLocal", session_local, raising=False)
    monkeypatch.setattr(metrics, "run_db", run_db, raising=False)

    from services.api.app.main import app

    later = now + timedelta(days=1)
    with TestClient(app) as client:
        resp = client.get(
            "/api/metrics/onboarding",
            params={"from": now.isoformat(), "to": later.isoformat()},
        )
    assert resp.status_code == 200
    assert resp.json() == {
        "A": {
            "onboarding_started": 1,
            "step_completed_1": 1,
            "step_completed_2": 0,
            "step_completed_3": 0,
            "onboarding_finished": 1,
            "onboarding_cancelled": 0,
        },
        "B": {
            "onboarding_started": 1,
            "step_completed_1": 0,
            "step_completed_2": 0,
            "step_completed_3": 0,
            "onboarding_finished": 0,
            "onboarding_cancelled": 0,
        },
    }
