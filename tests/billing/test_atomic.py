from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.billing.config import BillingSettings
from services.api.app.billing.log import BillingLog
from services.api.app.diabetes.services.db import Base, Subscription
from services.api.app.routers import billing
from services.api.app.main import app


# --- helpers -----------------------------------------------------------------


def setup_db() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Subscription.__table__, BillingLog.__table__])
    return sessionmaker(bind=engine, expire_on_commit=False)


def make_client(monkeypatch: pytest.MonkeyPatch, session_local: sessionmaker[Session]) -> TestClient:
    async def run_db(fn, *args, sessionmaker: sessionmaker[Session] = session_local, **kwargs):
        with sessionmaker() as session:
            return fn(session, *args, **kwargs)

    monkeypatch.setattr(billing, "run_db", run_db, raising=False)
    monkeypatch.setattr(billing, "SessionLocal", session_local, raising=False)
    settings = BillingSettings(
        billing_enabled=True,
        billing_test_mode=True,
        billing_provider="dummy",
        paywall_mode="soft",
        BILLING_ADMIN_TOKEN="secret",
    )
    client = TestClient(app)
    client.app.dependency_overrides[billing._require_billing_enabled] = lambda: settings
    return client


# --- tests -------------------------------------------------------------------


def test_start_trial_atomic(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    client = make_client(monkeypatch, session_local)

    orig = billing.log_billing_event

    def failing_log(session: Session, *args: object, **kwargs: object) -> None:
        orig(session, *args, **kwargs)
        raise RuntimeError("boom")

    monkeypatch.setattr(billing, "log_billing_event", failing_log)

    with pytest.raises(RuntimeError):
        client.post("/api/billing/trial", params={"user_id": 1})

    client.app.dependency_overrides.clear()

    count_stmt = select(func.count()).select_from(Subscription)
    log_stmt = select(func.count()).select_from(BillingLog)
    with session_local() as session:
        assert session.scalar(count_stmt) == 0
        assert session.scalar(log_stmt) == 0


def test_subscribe_atomic(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    client = make_client(monkeypatch, session_local)

    orig = billing.log_billing_event

    def failing_log(session: Session, *args: object, **kwargs: object) -> None:
        orig(session, *args, **kwargs)
        raise RuntimeError("boom")

    monkeypatch.setattr(billing, "log_billing_event", failing_log)

    with pytest.raises(RuntimeError):
        client.post("/api/billing/subscribe", params={"user_id": 1, "plan": "pro"})

    client.app.dependency_overrides.clear()

    count_stmt = select(func.count()).select_from(Subscription)
    log_stmt = select(func.count()).select_from(BillingLog)
    with session_local() as session:
        assert session.scalar(count_stmt) == 0
        assert session.scalar(log_stmt) == 0
