from __future__ import annotations

import logging
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
import pytest

from services.api.app.billing.config import BillingSettings
from services.api.app.diabetes.services.db import (
    Base,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)
from services.api.app.routers import billing
from services.api.app.main import app


def setup_db() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Subscription.__table__])
    return sessionmaker(bind=engine)


def make_client(
    monkeypatch: pytest.MonkeyPatch, session_local: sessionmaker[Session]
) -> TestClient:
    async def run_db(
        fn, *args, sessionmaker: sessionmaker[Session] = session_local, **kwargs
    ):
        with sessionmaker() as session:
            return fn(session, *args, **kwargs)

    monkeypatch.setattr(billing, "run_db", run_db, raising=False)
    monkeypatch.setattr(billing, "SessionLocal", session_local, raising=False)
    settings = BillingSettings(
        billing_enabled=True,
        billing_test_mode=True,
        billing_provider="dummy",
        paywall_mode="soft",
    )
    client = TestClient(app)
    client.app.dependency_overrides[billing._require_billing_enabled] = lambda: settings
    return client


def create_subscription(client: TestClient) -> str:
    resp = client.post("/api/billing/subscribe", params={"user_id": 1, "plan": "pro"})
    assert resp.status_code == 200
    return resp.json()["id"]


def test_webhook_activates_subscription(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    session_local = setup_db()
    client = make_client(monkeypatch, session_local)
    checkout_id = create_subscription(client)
    event = {
        "event_id": "evt1",
        "transaction_id": checkout_id,
        "plan": "pro",
        "signature": f"evt1:{checkout_id}",
    }
    caplog.set_level(logging.INFO)
    with client:
        resp = client.post("/api/billing/webhook", json=event)
    assert resp.status_code == 200
    assert resp.json() == {"status": "processed"}
    with session_local() as session:
        sub = session.scalar(
            select(Subscription).where(Subscription.transaction_id == checkout_id)
        )
        assert sub is not None
        assert sub.status == SubscriptionStatus.ACTIVE
        assert sub.plan == SubscriptionPlan.PRO
        assert sub.end_date is not None
    assert any("evt1 processed" in r.getMessage() for r in caplog.records)


def test_webhook_duplicate_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    client = make_client(monkeypatch, session_local)
    checkout_id = create_subscription(client)
    event = {
        "event_id": "evt2",
        "transaction_id": checkout_id,
        "plan": "pro",
        "signature": f"evt2:{checkout_id}",
    }
    with client:
        first = client.post("/api/billing/webhook", json=event)
    assert first.status_code == 200
    with session_local() as session:
        sub = session.scalar(
            select(Subscription).where(Subscription.transaction_id == checkout_id)
        )
        assert sub is not None
        first_end = sub.end_date

    with client:
        dup = client.post("/api/billing/webhook", json=event)
    assert dup.status_code == 200
    assert dup.json() == {"status": "ignored"}
    with session_local() as session:
        sub = session.scalar(
            select(Subscription).where(Subscription.transaction_id == checkout_id)
        )
        assert sub.end_date == first_end


def test_webhook_invalid_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    client = make_client(monkeypatch, session_local)
    checkout_id = create_subscription(client)
    event = {
        "event_id": "evt3",
        "transaction_id": checkout_id,
        "plan": "pro",
        "signature": "bad",
    }
    with client:
        resp = client.post("/api/billing/webhook", json=event)
    assert resp.status_code == 400
    with session_local() as session:
        sub = session.scalar(
            select(Subscription).where(Subscription.transaction_id == checkout_id)
        )
        assert sub is not None
        assert sub.status == SubscriptionStatus.PENDING
        assert sub.end_date is None
