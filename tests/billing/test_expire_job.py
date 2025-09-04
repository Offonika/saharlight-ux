from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, cast

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.services.db import (
    Base,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)
from services.api.app.billing.log import BillingEvent, BillingLog
from services.api.app.billing import jobs


def _setup_db() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Subscription.__table__, BillingLog.__table__])
    return sessionmaker(bind=engine)


@pytest.mark.asyncio
async def test_expire_subscriptions_logs_event(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    session_local = _setup_db()
    with session_local() as session:
        sub = Subscription(
            user_id=1,
            plan=SubscriptionPlan.PRO,
            status=SubscriptionStatus.TRIAL,
            provider="dummy",
            transaction_id="tx1",
            end_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        session.add(sub)
        session.commit()

    async def run_db(fn, *args, sessionmaker: sessionmaker[Session] = session_local, **kwargs) -> Any:
        with sessionmaker() as session:
            return fn(session, *args, **kwargs)

    monkeypatch.setattr(jobs, "run_db", run_db)
    monkeypatch.setattr(jobs, "_utcnow", lambda: datetime(2024, 1, 2, tzinfo=timezone.utc))

    caplog.set_level(logging.INFO)
    await jobs.expire_subscriptions(None)

    with session_local() as session:
        sub = session.scalar(select(Subscription))
        assert sub is not None
        assert sub.status == SubscriptionStatus.TRIAL
        log = session.scalar(
            select(BillingLog).where(
                BillingLog.user_id == 1,
                BillingLog.event == BillingEvent.EXPIRED,
            )
        )
        assert log is not None

    assert any("expired 1 subscription" in r.getMessage() for r in caplog.records)


def test_schedule_subscription_expiration_sets_job_kwargs() -> None:
    class DummyJob:
        next_run_time = None

    class DummyJobQueue:
        def __init__(self) -> None:
            self.kwargs: dict[str, object] | None = None

        def run_daily(self, callback, *, time, name, job_kwargs):  # type: ignore[override]
            self.kwargs = job_kwargs
            return DummyJob()

    jq = DummyJobQueue()
    jobs.schedule_subscription_expiration(cast(Any, jq))
    assert jq.kwargs == {"id": "subscriptions_expire", "replace_existing": True}


def test_schedule_subscription_expiration_skips_without_run_daily(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class Dummy:
        pass

    jq = Dummy()
    caplog.set_level(logging.INFO)
    jobs.schedule_subscription_expiration(cast(Any, jq))
    assert not any("subscriptions_expire" in r.getMessage() for r in caplog.records)


def test_utcnow_returns_aware_datetime() -> None:
    now = jobs._utcnow()
    assert now.tzinfo is timezone.utc
