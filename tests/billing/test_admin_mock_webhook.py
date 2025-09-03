from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.billing.config import BillingSettings
from services.api.app.diabetes.services.db import (
    Base,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)
from services.api.app.main import app
from services.api.app.routers import billing


# --- helpers ---------------------------------------------------------------


def setup_db() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Subscription.__table__])
    return sessionmaker(bind=engine)


def make_client(
    monkeypatch: pytest.MonkeyPatch,
    session_local: sessionmaker[Session],
    settings: BillingSettings,
) -> TestClient:
    async def run_db(
        fn, *args, sessionmaker: sessionmaker[Session] = session_local, **kwargs
    ):
        with sessionmaker() as session:
            return fn(session, *args, **kwargs)

    monkeypatch.setattr(billing, "run_db", run_db, raising=False)
    monkeypatch.setattr(billing, "SessionLocal", session_local, raising=False)
    client = TestClient(app)
    client.app.dependency_overrides[billing._require_billing_enabled] = lambda: settings
    return client


# --- tests -----------------------------------------------------------------


def test_admin_mock_webhook(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    settings = BillingSettings(
        BILLING_ENABLED=True,
        BILLING_TEST_MODE=True,
        BILLING_PROVIDER="dummy",
        PAYWALL_MODE="soft",
        BILLING_ADMIN_TOKEN="secret",
    )
    client = make_client(monkeypatch, session_local, settings)

    with session_local() as session:
        session.add(
            Subscription(
                user_id=1,
                plan=SubscriptionPlan.PRO,
                status=SubscriptionStatus.PENDING,
                provider="dummy",
                transaction_id="tx1",
                start_date=datetime.now(timezone.utc),
            )
        )
        session.commit()

    with client:
        resp = client.post(
            "/api/billing/admin/mock_webhook",
            params={"transaction_id": "tx1"},
            headers={"X-Admin-Token": "secret"},
        )
    assert resp.status_code == 200
    client.app.dependency_overrides.clear()

    with session_local() as session:
        sub = session.scalar(
            select(Subscription).where(Subscription.transaction_id == "tx1")
        )
        assert sub is not None
        assert sub.status == SubscriptionStatus.ACTIVE


def test_admin_mock_webhook_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    settings = BillingSettings(
        BILLING_ENABLED=True,
        BILLING_TEST_MODE=True,
        BILLING_PROVIDER="dummy",
        PAYWALL_MODE="soft",
        BILLING_ADMIN_TOKEN="secret",
    )
    client = make_client(monkeypatch, session_local, settings)

    with client:
        resp = client.post(
            "/api/billing/admin/mock_webhook",
            params={"transaction_id": "tx"},
        )
    assert resp.status_code == 403
    client.app.dependency_overrides.clear()


def test_admin_mock_webhook_disabled_in_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    settings = BillingSettings(
        BILLING_ENABLED=True,
        BILLING_TEST_MODE=False,
        BILLING_PROVIDER="dummy",
        PAYWALL_MODE="soft",
        BILLING_ADMIN_TOKEN="secret",
    )
    client = make_client(monkeypatch, session_local, settings)

    with client:
        resp = client.post(
            "/api/billing/admin/mock_webhook",
            params={"transaction_id": "tx"},
            headers={"X-Admin-Token": "secret"},
        )
    assert resp.status_code == 403
    client.app.dependency_overrides.clear()
