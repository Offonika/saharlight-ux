from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.routers import billing
from services.api.app.diabetes.services.db import (
    Base,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)


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
    from services.api.app.billing.config import BillingSettings

    async def run_db(
        fn, *args, sessionmaker: sessionmaker[Session] = session_local, **kwargs
    ):
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


def test_status_without_subscription(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    client = make_client(monkeypatch, session_local)
    with client:
        resp = client.get("/api/billing/status", params={"user_id": 1})
    assert resp.status_code == 200
    assert resp.json() == {
        "featureFlags": {
            "billingEnabled": False,
            "paywallMode": "soft",
            "testMode": True,
        },
        "subscription": None,
    }


def test_status_with_subscription(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()
    with session_local() as session:
        session.add(
            Subscription(
                user_id=1,
                plan=SubscriptionPlan.PRO,
                status=SubscriptionStatus.ACTIVE,
                provider="dummy",
                transaction_id="t1",
                start_date=datetime(2024, 1, 1),
                end_date=None,
            )
        )
        session.commit()

    client = make_client(monkeypatch, session_local)
    with client:
        resp = client.get("/api/billing/status", params={"user_id": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["featureFlags"] == {
        "billingEnabled": False,
        "paywallMode": "soft",
        "testMode": True,
    }
    assert data["subscription"]["plan"] == "pro"
    assert data["subscription"]["status"] == "active"
    assert data["subscription"]["provider"] == "dummy"
    assert data["subscription"]["startDate"].startswith("2024-01-01")
    assert data["subscription"]["endDate"] is None


def test_status_with_multiple_subscriptions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_local = setup_db()
    with session_local() as session:
        session.add_all(
            [
                Subscription(
                    user_id=1,
                    plan=SubscriptionPlan.PRO,
                    status=SubscriptionStatus.CANCELED,
                    provider="dummy",
                    transaction_id="t1",
                    start_date=datetime(2024, 1, 1),
                    end_date=datetime(2024, 2, 1),
                ),
                Subscription(
                    user_id=1,
                    plan=SubscriptionPlan.FAMILY,
                    status=SubscriptionStatus.ACTIVE,
                    provider="dummy",
                    transaction_id="t2",
                    start_date=datetime(2024, 3, 1),
                    end_date=None,
                ),
            ]
        )
        session.commit()

    client = make_client(monkeypatch, session_local)
    with client:
        resp = client.get("/api/billing/status", params={"user_id": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["featureFlags"] == {
        "billingEnabled": False,
        "paywallMode": "soft",
        "testMode": True,
    }
    assert data["subscription"]["plan"] == "family"
    assert data["subscription"]["status"] == "active"
    assert data["subscription"]["startDate"].startswith("2024-03-01")


def test_status_with_active_and_pending_subscriptions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_local = setup_db()
    with session_local() as session:
        session.add_all(
            [
                Subscription(
                    user_id=1,
                    plan=SubscriptionPlan.PRO,
                    status=SubscriptionStatus.ACTIVE,
                    provider="dummy",
                    transaction_id="t1",
                    start_date=datetime(2024, 1, 1),
                    end_date=None,
                ),
                Subscription(
                    user_id=1,
                    plan=SubscriptionPlan.FAMILY,
                    status=SubscriptionStatus.PENDING,
                    provider="dummy",
                    transaction_id="t2",
                    start_date=datetime(2024, 4, 1),
                    end_date=None,
                ),
            ]
        )
        session.commit()

    client = make_client(monkeypatch, session_local)
    with client:
        resp = client.get("/api/billing/status", params={"user_id": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["subscription"]["status"] == "active"
    assert data["subscription"]["plan"] == "pro"
    assert data["subscription"]["startDate"].startswith("2024-01-01")


def test_duplicate_status_per_user() -> None:
    session_local = setup_db()
    with session_local() as session:
        session.add(
            Subscription(
                user_id=1,
                plan=SubscriptionPlan.PRO,
                status=SubscriptionStatus.ACTIVE,
                provider="dummy",
                transaction_id="t1",
                start_date=datetime(2024, 1, 1),
                end_date=None,
            )
        )
        session.add(
            Subscription(
                user_id=1,
                plan=SubscriptionPlan.FAMILY,
                status=SubscriptionStatus.ACTIVE,
                provider="dummy",
                transaction_id="t2",
                start_date=datetime(2024, 2, 1),
                end_date=None,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
