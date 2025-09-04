from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session as SASession

from services.api.app.billing.config import BillingSettings
from services.api.app.billing.log import BillingEvent, BillingLog
from services.api.app.diabetes.services.db import Base, Subscription
from services.api.app.routers import billing
from services.api.app.main import app


# --- helpers ---------------------------------------------------------------

def setup_db() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Subscription.__table__, BillingLog.__table__])
    return sessionmaker(bind=engine, expire_on_commit=False)


def make_client(
    monkeypatch: pytest.MonkeyPatch, session_local: sessionmaker[Session]
) -> TestClient:
    async def run_db(fn, *args, **kwargs):
        kwargs.pop("sessionmaker", None)
        with session_local() as session:
            return fn(session, *args, **kwargs)

    monkeypatch.setattr(billing, "run_db", run_db, raising=False)
    settings = BillingSettings(
        billing_enabled=True,
        billing_test_mode=True,
        billing_provider="dummy",
        paywall_mode="soft",
        BILLING_ADMIN_TOKEN="secret",
    )
    client = TestClient(app, raise_server_exceptions=False)
    client.app.dependency_overrides[billing._require_billing_enabled] = lambda: settings
    return client


# --- tests -----------------------------------------------------------------


def test_subscribe_persists_subscription_and_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_local = setup_db()
    client = make_client(monkeypatch, session_local)
    with client:
        resp = client.post(
            "/api/billing/subscribe", params={"user_id": 1, "plan": "pro"}
        )
    assert resp.status_code == 200
    client.app.dependency_overrides.clear()
    with session_local() as session:
        sub = session.scalar(select(Subscription))
        assert sub is not None
        logs = session.scalars(select(BillingLog)).all()
        assert [log.event for log in logs] == [
            BillingEvent.INIT,
            BillingEvent.CHECKOUT_CREATED,
        ]


def test_subscribe_rollback_on_commit_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_local = setup_db()
    client = make_client(monkeypatch, session_local)

    def fail_commit(self) -> None:  # type: ignore[unused-argument]
        raise RuntimeError("boom")

    monkeypatch.setattr(SASession, "commit", fail_commit, raising=False)

    with client:
        resp = client.post(
            "/api/billing/subscribe", params={"user_id": 1, "plan": "pro"}
        )
    assert resp.status_code == 500
    client.app.dependency_overrides.clear()
    with session_local() as session:
        assert session.scalar(select(Subscription)) is None
        assert session.scalar(select(BillingLog)) is None
