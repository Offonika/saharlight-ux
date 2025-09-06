from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from services.api.app.billing import reload_billing_settings
from services.api.app.billing.providers.dummy import DummyBillingProvider
from services.api.app.diabetes.services.db import (
    Base,
    Subscription,
    SubscriptionPlan,
    SubStatus,
)
from services.api.app.billing.log import BillingLog
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


# --- tests -----------------------------------------------------------------


def test_subscribe_billing_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BILLING_ENABLED", "false")
    reload_billing_settings()
    with TestClient(app) as client:
        resp = client.post("/api/billing/subscribe", params={"user_id": 1, "plan": "pro"})
    assert resp.status_code == 503


def test_subscribe_dummy_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    client = make_client(monkeypatch, session_local)
    with client:
        resp = client.post(
            "/api/billing/subscribe", params={"user_id": 1, "plan": "pro"}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert set(data) == {"checkout_id"}
    assert data["checkout_id"].startswith("dummy-")

    with session_local() as session:
        sub = session.scalar(
            select(Subscription).where(
                Subscription.transaction_id == data["checkout_id"]
            )
        )
        assert sub is not None
        assert sub.status == SubStatus.pending
        assert sub.plan == SubscriptionPlan.PRO
        assert sub.end_date is not None

    with client:
        webhook = client.post(
            f"/api/billing/mock-webhook/{data['checkout_id']}",
            headers={"X-Admin-Token": "secret"},
        )
    assert webhook.status_code == 200

    with session_local() as session:
        sub = session.scalar(
            select(Subscription).where(
                Subscription.transaction_id == data["checkout_id"]
            )
        )
        assert sub is not None
        assert sub.status == SubStatus.active
        assert sub.plan == SubscriptionPlan.PRO


def test_mock_webhook_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    client = make_client(monkeypatch, session_local)
    with client:
        resp = client.post(
            "/api/billing/subscribe", params={"user_id": 1, "plan": "pro"}
        )
    assert resp.status_code == 200
    data = resp.json()

    with client:
        webhook = client.post(
            f"/api/billing/mock-webhook/{data['checkout_id']}"
        )
    assert webhook.status_code == 403


def test_provider_gets_plan_str(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    async def fake_create_checkout(self, plan: str) -> dict[str, str]:  # pragma: no cover
        raise AssertionError("should not be called")

    monkeypatch.setattr(
        DummyBillingProvider, "create_checkout", fake_create_checkout, raising=False
    )
    client = make_client(monkeypatch, session_local)
    with client:
        resp = client.post(
            "/api/billing/subscribe", params={"user_id": 1, "plan": "pro"}
        )
    assert resp.status_code == 200


def test_subscribe_duplicate(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    client = make_client(monkeypatch, session_local)
    with client:
        first = client.post("/api/billing/subscribe", params={"user_id": 1, "plan": "pro"})
    assert first.status_code == 200
    with client:
        second = client.post("/api/billing/subscribe", params={"user_id": 1, "plan": "pro"})
    assert second.status_code == 409
    assert second.json() == {"detail": "subscription already exists"}
    with session_local() as session:
        subs = session.scalars(select(Subscription)).all()
        assert len(subs) == 1


def test_subscribe_conflict_with_existing_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_local = setup_db()
    with session_local() as session:
        session.add(
            Subscription(
                user_id=1,
                plan=SubscriptionPlan.PRO,
                status=SubStatus.active,
                provider="dummy",
                transaction_id="existing",
                start_date=datetime.now(timezone.utc),
                end_date=None,
            )
        )
        session.commit()
    client = make_client(monkeypatch, session_local)
    with client:
        resp = client.post("/api/billing/subscribe", params={"user_id": 1, "plan": "pro"})
    assert resp.status_code == 409
    assert resp.json() == {"detail": "subscription already exists"}
