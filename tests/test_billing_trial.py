from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.routers import billing
from services.api.app.diabetes.services.db import (
    Base,
    Subscription,
    SubscriptionStatus,
)
from services.api.app.billing.log import BillingEvent, BillingLog


# --- helpers -----------------------------------------------------------------


def setup_db() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Subscription.__table__, BillingLog.__table__])
    return sessionmaker(bind=engine)


def make_client(monkeypatch: pytest.MonkeyPatch, session_local: sessionmaker[Session]) -> TestClient:
    from services.api.app.billing.config import BillingSettings

    async def run_db(fn, *args, sessionmaker: sessionmaker[Session] = session_local, **kwargs):
        with sessionmaker() as session:
            return fn(session, *args, **kwargs)

    monkeypatch.setattr(billing, "run_db", run_db, raising=False)
    monkeypatch.setattr(billing, "SessionLocal", session_local, raising=False)
    monkeypatch.setattr(
        billing,
        "get_billing_settings",
        lambda: BillingSettings(
            billing_enabled=False,
            billing_test_mode=True,
            billing_provider="dummy",
            paywall_mode="soft",
        ),
        raising=False,
    )

    from services.api.app.main import app

    return TestClient(app)


# --- tests --------------------------------------------------------------------


def test_trial_creation(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    client = make_client(monkeypatch, session_local)
    with client:
        resp = client.post("/api/billing/trial", params={"user_id": 1})
        status_resp = client.get("/api/billing/status", params={"user_id": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "pro"
    assert data["status"] == SubscriptionStatus.TRIAL.value
    start = datetime.fromisoformat(data["startDate"])
    end = datetime.fromisoformat(data["endDate"])
    assert end - start == timedelta(days=14)
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    sub = status_data["subscription"]
    assert sub["plan"] == "pro"
    assert sub["status"] == SubscriptionStatus.TRIAL.value
    assert sub["provider"] == "trial"
    assert sub["endDate"] == data["endDate"]
    count_stmt = select(func.count()).select_from(Subscription)
    log_stmt = (
        select(func.count())
        .select_from(BillingLog)
        .where(BillingLog.user_id == 1, BillingLog.event == BillingEvent.INIT)
    )
    with session_local() as session:
        count = session.scalar(count_stmt)
        log_count = session.scalar(log_stmt)
    assert count == 1
    assert log_count == 1


def test_trial_repeat_call(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    client = make_client(monkeypatch, session_local)
    with client:
        resp1 = client.post("/api/billing/trial", params={"user_id": 1})
        resp2 = client.post("/api/billing/trial", params={"user_id": 1})
    assert resp1.status_code == 200
    assert resp1.json() == resp2.json()
    count_stmt = select(func.count()).select_from(Subscription)
    log_stmt = (
        select(func.count())
        .select_from(BillingLog)
        .where(BillingLog.user_id == 1, BillingLog.event == BillingEvent.INIT)
    )
    with session_local() as session:
        count = session.scalar(count_stmt)
        log_count = session.scalar(log_stmt)
    assert count == 1
    assert log_count == 1
