from datetime import time

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from services.api.app.diabetes.services.db import Base, Reminder


def _session_factory() -> sessionmaker[Session]:
    engine = sa.create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, class_=Session)


def test_invalid_reminder_type() -> None:
    SessionLocal = _session_factory()
    with SessionLocal() as session:
        session.add(Reminder(type="sugar", time=time(8, 0)))
        session.commit()
        session.add(Reminder(type="bad", time=time(8, 0)))
        with pytest.raises(sa.exc.StatementError):
            session.commit()


def test_invalid_schedule_kind() -> None:
    SessionLocal = _session_factory()
    with SessionLocal() as session:
        session.add(Reminder(type="sugar", kind="at_time", time=time(9, 0)))
        session.commit()
        session.add(Reminder(type="sugar", kind="nope", time=time(9, 0)))
        with pytest.raises(sa.exc.StatementError):
            session.commit()

