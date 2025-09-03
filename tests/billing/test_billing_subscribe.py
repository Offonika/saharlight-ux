from __future__ import annotations

from fastapi.testclient import TestClient
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from services.api.app.diabetes.services.db import (
    Base,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    BillingLog,
    BillingEvent,
)
from services.api.app.routers import billing
from services.api.app.billing.config import BillingSettings
from services.api.app.main import app


# --- helpers ---------------------------------------------------------------


def setup_db() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Subscription.__table__, BillingLog.__table__])
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


# --- tests -----------------------------------------------------------------


def test_subscribe_billing_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    client = TestClient(app)
    client.app.dependency_overrides[billing._require_billing_enabled] = (
        lambda: (_ for _ in ()).throw(HTTPException(status_code=503))
    )
    with client:
        resp = client.post(
            "/api/billing/subscribe", params={"user_id": 1, "plan": "pro"}
        )
    assert resp.status_code == 503
    client.app.dependency_overrides.clear()


def test_subscribe_dummy_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    client = make_client(monkeypatch, session_local)
    with client:
        resp = client.post(
            "/api/billing/subscribe", params={"user_id": 1, "plan": "pro"}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert set(data) == {"id", "url"}

    with client:
        webhook = client.post(f"/api/billing/mock-webhook/{data['id']}")
    assert webhook.status_code == 200

    with session_local() as session:
        sub = session.scalar(
            select(Subscription).where(Subscription.transaction_id == data["id"])
        )
        assert sub is not None
        assert sub.status == SubscriptionStatus.ACTIVE
        assert sub.plan == SubscriptionPlan.PRO
        logs = session.scalars(select(BillingLog).order_by(BillingLog.id)).all()
    assert [log.event for log in logs] == [
        BillingEvent.CHECKOUT_CREATED,
        BillingEvent.WEBHOOK_OK,
    ]
