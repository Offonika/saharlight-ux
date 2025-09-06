from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from services.api.app.billing.log import BillingLog, BillingEvent, log_billing_event
from services.api.app.diabetes.services.db import (
    Base,
    Subscription,
    SubscriptionPlan,
    SubStatus,
    run_db,
)


def _setup_db() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Subscription.__table__, BillingLog.__table__])
    return sessionmaker(bind=engine)


@pytest.mark.asyncio
async def test_subscription_creation_atomicity() -> None:
    """Subscription draft and logs should persist atomically."""

    session_local = _setup_db()

    async def _create_and_fail() -> None:
        def _op(session: Session) -> None:
            draft = Subscription(
                user_id=1,
                plan=SubscriptionPlan.PRO,
                status=SubStatus.pending,
                provider="dummy",
                transaction_id="tx",
                end_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )
            session.add(draft)
            log_billing_event(
                session,
                1,
                BillingEvent.INIT,
                {"plan": SubscriptionPlan.PRO.value},
            )
            log_billing_event(
                session,
                1,
                BillingEvent.CHECKOUT_CREATED,
                {"plan": SubscriptionPlan.PRO.value, "checkout_id": "tx"},
            )
            raise RuntimeError

        await run_db(_op, sessionmaker=session_local)

    with pytest.raises(RuntimeError):
        await _create_and_fail()

    with session_local() as session:
        assert session.scalars(select(Subscription)).all() == []
        assert session.scalars(select(BillingLog)).all() == []
