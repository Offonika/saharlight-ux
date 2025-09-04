from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from services.api.app.billing import reload_billing_settings
from services.api.app.diabetes.services.db import (
    Base,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)
from services.api.app.billing.log import BillingEvent, BillingLog
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
    Base.metadata.create_all(
        engine, tables=[Subscription.__table__, BillingLog.__table__]
    )
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
        resp = client.post(
            "/api/billing/subscribe", params={"user_id": 1, "plan": "pro"}
        )
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
    assert set(data) == {"id", "url"}
    assert "mock-checkout" in data["url"]

    with client:
        webhook = client.post(
            f"/api/billing/mock-webhook/{data['id']}",
            headers={"X-Admin-Token": "secret"},
        )
    assert webhook.status_code == 200

    with session_local() as session:
        sub = session.scalar(
            select(Subscription).where(Subscription.transaction_id == data["id"])
        )
        assert sub is not None
        assert sub.status == SubscriptionStatus.ACTIVE
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
        webhook = client.post(f"/api/billing/mock-webhook/{data['id']}")
    assert webhook.status_code == 403


def test_subscribe_log_failure_rolled_back(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    client = make_client(monkeypatch, session_local)
    original = billing.log_billing_event

    def failing_log(*args: object, **kwargs: object) -> None:
        original(*args, **kwargs)
        raise RuntimeError

    monkeypatch.setattr(billing, "log_billing_event", failing_log)
    with pytest.raises(RuntimeError):
        with client:
            client.post("/api/billing/subscribe", params={"user_id": 1, "plan": "pro"})
    count_stmt = select(func.count()).select_from(Subscription)
    log_stmt = select(func.count()).select_from(BillingLog)
    with session_local() as session:
        count = session.scalar(count_stmt)
        log_count = session.scalar(log_stmt)
    assert count == 0
    assert log_count == 0


def test_mock_webhook_log_failure_rolled_back(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    client = make_client(monkeypatch, session_local)
    with client:
        resp = client.post(
            "/api/billing/subscribe", params={"user_id": 1, "plan": "pro"}
        )
    checkout_id = resp.json()["id"]
    original = billing.log_billing_event

    def failing_log(*args: object, **kwargs: object) -> None:
        original(*args, **kwargs)
        raise RuntimeError

    monkeypatch.setattr(billing, "log_billing_event", failing_log)
    with pytest.raises(RuntimeError):
        with client:
            client.post(
                f"/api/billing/mock-webhook/{checkout_id}",
                headers={"X-Admin-Token": "secret"},
            )
    with session_local() as session:
        sub = session.scalar(
            select(Subscription).where(Subscription.transaction_id == checkout_id)
        )
        assert sub is not None
        assert sub.status == SubscriptionStatus.PENDING
        assert sub.end_date is None
        log_count = session.scalar(
            select(func.count())
            .select_from(BillingLog)
            .where(BillingLog.event == BillingEvent.WEBHOOK_OK)
        )
        assert log_count == 0
