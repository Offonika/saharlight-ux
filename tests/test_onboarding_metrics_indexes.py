from __future__ import annotations

from datetime import date, datetime, UTC
from typing import Any

import sqlalchemy as sa
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.services import db
from services.api.app.models.onboarding_metrics import (
    OnboardingMetricDaily,
    OnboardingMetricEvent,
)


def setup_db() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)
    return SessionLocal


def test_onboarding_events_metrics_index_exists() -> None:
    SessionLocal = setup_db()
    with SessionLocal() as session:
        session.add(
            OnboardingMetricEvent(
                variant="v1",
                step="s1",
                created_at=datetime.now(UTC),
            )
        )
        session.commit()
        indexes = session.execute(
            sa.text("PRAGMA index_list('onboarding_events_metrics')")
        ).all()
        assert any(
            row[1] == "ix_onboarding_events_metrics_variant_step_created_at"
            for row in indexes
        )


def test_onboarding_metrics_daily_index_exists() -> None:
    SessionLocal = setup_db()
    with SessionLocal() as session:
        session.add(
            OnboardingMetricDaily(
                date=date(2024, 1, 1), variant="v1", step="s1", count=1
            )
        )
        session.commit()
        indexes = session.execute(
            sa.text("PRAGMA index_list('onboarding_metrics_daily')")
        ).all()
        assert any(
            row[1] == "ix_onboarding_metrics_daily_date_variant_step" for row in indexes
        )
