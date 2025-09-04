from __future__ import annotations

from datetime import datetime, timedelta

import asyncio
import logging
from typing import Any, Callable, cast

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from psycopg2.errors import InvalidTextRepresentation
from sqlalchemy import create_engine, func, select
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
from services.api.app.billing.log import BillingEvent, BillingLog


def parse_iso(dt: str) -> datetime:
    return datetime.fromisoformat(dt.replace("Z", "+00:00")).replace(tzinfo=None)


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
    from services.api.app.billing.config import BillingSettings

    async def run_db(fn, *args, sessionmaker: sessionmaker[Session] = session_local, **kwargs):
        with sessionmaker() as session:
            return fn(session, *args, **kwargs)

    monkeypatch.setattr(billing, "run_db", run_db, raising=False)
    monkeypatch.setattr(billing, "SessionLocal", session_local, raising=False)

    from services.api.app.main import app

    app.dependency_overrides[billing._require_billing_enabled] = lambda: BillingSettings(
        billing_enabled=True,
        billing_test_mode=True,
        billing_provider="dummy",
        paywall_mode="soft",
    )

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
    assert parse_iso(sub["endDate"]) == parse_iso(data["endDate"])
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
    data1 = resp1.json()
    data2 = resp2.json()
    assert data1["plan"] == data2["plan"] == "pro"
    assert data1["status"] == data2["status"] == SubscriptionStatus.TRIAL.value
    assert parse_iso(data1["endDate"]) == parse_iso(data2["endDate"])
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


def test_trial_repeat_call_after_expiration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_local = setup_db()
    client = make_client(monkeypatch, session_local)
    with client:
        resp1 = client.post("/api/billing/trial", params={"user_id": 1})
    assert resp1.status_code == 200
    data1 = resp1.json()

    future = parse_iso(data1["endDate"]) + timedelta(days=1)

    class FakeDatetime:
        @staticmethod
        def now(tz: object | None = None) -> datetime:
            return future

    monkeypatch.setattr(billing, "datetime", FakeDatetime)
    with client:
        resp2 = client.post("/api/billing/trial", params={"user_id": 1})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["plan"] == "pro"
    assert data2["status"] == SubscriptionStatus.TRIAL.value
    assert parse_iso(data1["endDate"]) == parse_iso(data2["endDate"])
    count_stmt = select(func.count()).select_from(Subscription)
    with session_local() as session:
        count = session.scalar(count_stmt)
    assert count == 1


def test_trial_integrity_error(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    session_local = setup_db()
    client = make_client(monkeypatch, session_local)
    calls: dict[str, int] = {"n": 0}

    async def run_db_err(*_args: object, **_kwargs: object) -> None:
        if calls["n"] == 0:
            calls["n"] += 1
            raise IntegrityError("", {"user_id": 1, "status": "trial", "plan": "pro"}, None)
        return None

    monkeypatch.setattr(billing, "run_db", run_db_err, raising=False)
    with caplog.at_level(logging.WARNING):
        with client:
            resp = client.post("/api/billing/trial", params={"user_id": 1})
    assert resp.status_code == 409
    assert resp.json()["detail"] == "trial already exists"
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.user_id == 1
    assert record.status == SubscriptionStatus.TRIAL.value
    assert record.plan == SubscriptionPlan.PRO.value
    assert record.params == {"user_id": 1, "status": "trial", "plan": "pro"}


def test_trial_invalid_enum(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    session_local = setup_db()
    client = make_client(monkeypatch, session_local)
    calls: dict[str, int] = {"n": 0}

    async def run_db_err(*_args: object, **_kwargs: object) -> None:
        if calls["n"] == 0:
            calls["n"] += 1
            raise InvalidTextRepresentation("invalid enum")
        return None

    monkeypatch.setattr(billing, "run_db", run_db_err, raising=False)
    with caplog.at_level(logging.WARNING):
        with client:
            resp = client.post("/api/billing/trial", params={"user_id": 1})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid enum value"
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.user_id == 1
    assert record.status == SubscriptionStatus.TRIAL.value
    assert record.plan == SubscriptionPlan.PRO.value
    assert record.params is None


@pytest.mark.asyncio
async def test_trial_parallel_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    session_local = setup_db()

    from services.api.app.billing.config import BillingSettings

    async def run_db(
        fn: Callable[..., Any],
        *args: Any,
        sessionmaker: sessionmaker[Session] = session_local,
        **kwargs: Any,
    ) -> Any:
        with sessionmaker() as session:
            return fn(session, *args, **kwargs)

    monkeypatch.setattr(billing, "run_db", run_db, raising=False)
    monkeypatch.setattr(billing, "SessionLocal", session_local, raising=False)
    from services.api.app.main import app

    app.dependency_overrides[billing._require_billing_enabled] = lambda: BillingSettings(
        billing_enabled=True,
        billing_test_mode=True,
        billing_provider="dummy",
        paywall_mode="soft",
    )

    async with AsyncClient(transport=ASGITransport(app=cast(Any, app)), base_url="http://test") as ac:
        resp1, resp2 = await asyncio.gather(
            ac.post("/api/billing/trial", params={"user_id": 1}),
            ac.post("/api/billing/trial", params={"user_id": 1}),
        )

    assert resp1.status_code == 200
    data1 = resp1.json()
    data2 = resp2.json()
    assert data1["plan"] == data2["plan"] == "pro"
    assert data1["status"] == data2["status"] == SubscriptionStatus.TRIAL.value
    assert parse_iso(data1["endDate"]) == parse_iso(data2["endDate"])
    count_stmt = select(func.count()).select_from(Subscription)
    with session_local() as session:
        count = session.scalar(count_stmt)
    assert count == 1
