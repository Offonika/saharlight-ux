from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session, sessionmaker

import pytest

from services.api.app.diabetes.services.db import (
    Base,
    Reminder,
    ReminderType,
    ScheduleKind,
)


def _setup_session() -> sessionmaker[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_invalid_reminder_type() -> None:
    Session = _setup_session()
    with Session() as session:
        session.add(Reminder(type=ReminderType.sugar))
        session.commit()
        session.add(Reminder(type="invalid"))  # type: ignore[arg-type]
        with pytest.raises((ValueError, StatementError, IntegrityError)):
            session.commit()
        session.rollback()


def test_invalid_schedule_kind() -> None:
    Session = _setup_session()
    with Session() as session:
        session.add(Reminder(type=ReminderType.sugar, kind=ScheduleKind.at_time))
        session.commit()
        session.add(
            Reminder(type=ReminderType.sugar, kind="bad")  # type: ignore[arg-type]
        )
        with pytest.raises((ValueError, StatementError, IntegrityError)):
            session.commit()
        session.rollback()
