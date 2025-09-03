from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession, sessionmaker

from services.api.app.diabetes.services import db
from services.api.app.management import aggregate_onboarding
from services.api.app.models.onboarding_metrics import (
    OnboardingEvent,
    OnboardingMetricDaily,
)


@pytest.fixture()
def session_local(monkeypatch: pytest.MonkeyPatch) -> sessionmaker[SASession]:
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine, class_=SASession)
    db.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(db, "SessionLocal", SessionLocal, raising=False)
    monkeypatch.setattr(
        aggregate_onboarding, "SessionLocal", SessionLocal, raising=False
    )
    yield SessionLocal
    engine.dispose()


def test_aggregate_onboarding(session_local: sessionmaker[SASession]) -> None:
    target = date(2024, 1, 2)
    with session_local() as session:
        session.add_all(
            [
                OnboardingEvent(
                    variant="A", step="start", created_at=datetime(2024, 1, 2, 1)
                ),
                OnboardingEvent(
                    variant="A", step="start", created_at=datetime(2024, 1, 2, 2)
                ),
                OnboardingEvent(
                    variant="A", step="finish", created_at=datetime(2024, 1, 2, 3)
                ),
                OnboardingEvent(
                    variant="B", step="start", created_at=datetime(2024, 1, 3, 1)
                ),
            ]
        )
        session.commit()

    metrics = aggregate_onboarding.aggregate_for_date(
        target, sessionmaker=session_local
    )
    assert {"variant": "A", "step": "start", "count": 2} in metrics
    assert {"variant": "A", "step": "finish", "count": 1} in metrics
    assert all(m["variant"] != "B" for m in metrics)

    with session_local() as session:
        rows = session.query(OnboardingMetricDaily).all()
        assert len(rows) == 2
        counts = {(r.variant, r.step): r.count for r in rows}
        assert counts[("A", "start")] == 2
        assert counts[("A", "finish")] == 1
