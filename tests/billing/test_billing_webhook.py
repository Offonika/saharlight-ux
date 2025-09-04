from __future__ import annotations

import hashlib
import hmac
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
from services.api.app.billing.log import BillingEvent, BillingLog
from services.api.app.routers import billing
from services.api.app.main import app


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
    monkeypatch: pytest.MonkeyPatch,
    session_local: sessionmaker[Session],
    **settings_kwargs: object,
) -> TestClient:
    async def run_db(
        fn, *args, sessionmaker: sessionmaker[Session] = session_local, **kwargs
    ):
        with sessionmaker() as session:
            return fn(session, *args, **kwargs)

    monkeypatch.setattr(billing, "run_db", run_db, raising=False)
    monkeypatch.setattr(billing, "SessionLocal", session_local, raising=False)
    settings = BillingSettings(
        BILLING_ENABLED=True,
        BILLING_TEST_MODE=True,
        BILLING_PROVIDER="dummy",
        PAYWALL_MODE="soft",
        _env_file=None,
        **settings_kwargs,
    )
    client = TestClient(app)
    client.app.dependency_overrides[billing._require_billing_enabled] = lambda: settings
    return client


def create_subscription(client: TestClient) -> str:
    resp = client.post("/api/billing/subscribe", params={"user_id": 1, "plan": "pro"})
    assert resp.status_code == 200
    return resp.json()["id"]


def _sign(secret: str, event_id: str, transaction_id: str) -> str:
    payload = f"{event_id}:{transaction_id}".encode()
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def test_webhook_activates_subscription(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    session_local = setup_db()
    secret = "testsecret"
    client = make_client(monkeypatch, session_local, BILLING_WEBHOOK_SECRET=secret)
    checkout_id = create_subscription(client)
    event_id = "evt1"
    sig = _sign(secret, event_id, checkout_id)
    event = {
        "event_id": event_id,
        "transaction_id": checkout_id,
        "plan": "pro",
        "signature": sig,
    }
    caplog.set_level(logging.INFO)
    with client:
        resp = client.post(
            "/api/billing/webhook", json=event, headers={"X-Webhook-Signature": sig}
        )
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
        log = session.scalar(
            select(BillingLog).where(
                BillingLog.user_id == 1,
                BillingLog.event == BillingEvent.WEBHOOK_OK,
            )
        )
        assert log is not None
    assert any(f"{checkout_id} processed" in r.getMessage() for r in caplog.records)


def test_webhook_duplicate_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    secret = "testsecret"
    client = make_client(monkeypatch, session_local, BILLING_WEBHOOK_SECRET=secret)
    checkout_id = create_subscription(client)
    event_id = "evt2"
    sig = _sign(secret, event_id, checkout_id)
    event = {
        "event_id": event_id,
        "transaction_id": checkout_id,
        "plan": "pro",
        "signature": sig,
    }
    with client:
        first = client.post(
            "/api/billing/webhook", json=event, headers={"X-Webhook-Signature": sig}
        )
    assert first.status_code == 200
    with session_local() as session:
        sub = session.scalar(
            select(Subscription).where(Subscription.transaction_id == checkout_id)
        )
        assert sub is not None
        first_end = sub.end_date

    with client:
        dup = client.post(
            "/api/billing/webhook", json=event, headers={"X-Webhook-Signature": sig}
        )
    assert dup.status_code == 200
    assert dup.json() == {"status": "ignored"}
    with session_local() as session:
        subs = session.scalars(select(Subscription)).all()
        assert len(subs) == 1
        assert subs[0].end_date == first_end


def test_webhook_invalid_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    secret = "testsecret"
    client = make_client(monkeypatch, session_local, BILLING_WEBHOOK_SECRET=secret)
    checkout_id = create_subscription(client)
    event_id = "evt3"
    bad_sig = "bad"
    event = {
        "event_id": event_id,
        "transaction_id": checkout_id,
        "plan": "pro",
        "signature": bad_sig,
    }
    with client:
        resp = client.post(
            "/api/billing/webhook", json=event, headers={"X-Webhook-Signature": bad_sig}
        )
    assert resp.status_code == 400
    with session_local() as session:
        sub = session.scalar(
            select(Subscription).where(Subscription.transaction_id == checkout_id)
        )
        assert sub is not None
        assert sub.status == SubscriptionStatus.PENDING
        assert sub.end_date is None


def test_webhook_signature_header_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    secret = "testsecret"
    client = make_client(monkeypatch, session_local, BILLING_WEBHOOK_SECRET=secret)
    checkout_id = create_subscription(client)
    event_id = "evt_header_mismatch"
    sig = _sign(secret, event_id, checkout_id)
    event = {
        "event_id": event_id,
        "transaction_id": checkout_id,
        "plan": "pro",
        "signature": sig,
    }
    with client:
        resp = client.post(
            "/api/billing/webhook", json=event, headers={"X-Webhook-Signature": "wrong"}
        )
    assert resp.status_code == 400
    with session_local() as session:
        sub = session.scalar(
            select(Subscription).where(Subscription.transaction_id == checkout_id)
        )
        assert sub is not None
        assert sub.status == SubscriptionStatus.PENDING
        assert sub.end_date is None


def test_webhook_rejects_unknown_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    secret = "testsecret"
    client = make_client(
        monkeypatch,
        session_local,
        BILLING_WEBHOOK_SECRET=secret,
        BILLING_WEBHOOK_IPS="1.2.3.4",
    )
    checkout_id = create_subscription(client)
    event_id = "evt4"
    sig = _sign(secret, event_id, checkout_id)
    event = {
        "event_id": event_id,
        "transaction_id": checkout_id,
        "plan": "pro",
        "signature": sig,
    }
    with client:
        resp = client.post(
            "/api/billing/webhook",
            json=event,
            headers={
                "X-Webhook-Signature": sig,
                "X-Forwarded-For": "5.6.7.8",
            },
        )
    assert resp.status_code == 400


def test_webhook_accepts_first_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    secret = "testsecret"
    client = make_client(
        monkeypatch,
        session_local,
        BILLING_WEBHOOK_SECRET=secret,
        BILLING_WEBHOOK_IPS="1.2.3.4",
    )
    checkout_id = create_subscription(client)
    event_id = "evt5"
    sig = _sign(secret, event_id, checkout_id)
    event = {
        "event_id": event_id,
        "transaction_id": checkout_id,
        "plan": "pro",
        "signature": sig,
    }
    with client:
        resp = client.post(
            "/api/billing/webhook",
            json=event,
            headers={
                "X-Webhook-Signature": sig,
                "X-Forwarded-For": "1.2.3.4, 5.6.7.8",
            },
        )
    assert resp.status_code == 200
    assert resp.json() == {"status": "processed"}


def test_webhook_conflict_with_existing_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_local = setup_db()
    secret = "testsecret"
    client = make_client(monkeypatch, session_local, BILLING_WEBHOOK_SECRET=secret)

    # first subscription activated
    checkout1 = create_subscription(client)
    event_id1 = "evt_active_first"
    sig1 = _sign(secret, event_id1, checkout1)
    event1 = {
        "event_id": event_id1,
        "transaction_id": checkout1,
        "plan": "pro",
        "signature": sig1,
    }
    with client:
        resp1 = client.post(
            "/api/billing/webhook", json=event1, headers={"X-Webhook-Signature": sig1}
        )
    assert resp1.status_code == 200

    # second subscription pending
    checkout2 = create_subscription(client)
    event_id2 = "evt_conflict"
    sig2 = _sign(secret, event_id2, checkout2)
    event2 = {
        "event_id": event_id2,
        "transaction_id": checkout2,
        "plan": "pro",
        "signature": sig2,
    }
    with client:
        resp2 = client.post(
            "/api/billing/webhook", json=event2, headers={"X-Webhook-Signature": sig2}
        )
    assert resp2.status_code == 409
    with session_local() as session:
        active = session.scalars(
            select(Subscription).where(
                Subscription.user_id == 1,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        ).all()
        assert len(active) == 1
        assert active[0].transaction_id == checkout1
