from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.billing.log import BillingLog, BillingEvent, log_billing_event
from services.api.app.diabetes.services.db import Base


def _session_local() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[BillingLog.__table__])
    return sessionmaker(bind=engine)


def test_log_billing_event_persists() -> None:
    session_local = _session_local()
    with session_local() as session:
        log_billing_event(session, 1, BillingEvent.INIT, {"foo": "bar"})
    with session_local() as session:
        logs = session.scalars(select(BillingLog)).all()
        assert len(logs) == 1
        log = logs[0]
        assert log.user_id == 1
        assert log.event is BillingEvent.INIT
        assert log.context == {"foo": "bar"}
