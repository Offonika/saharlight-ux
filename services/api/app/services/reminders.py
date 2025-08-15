from __future__ import annotations

from typing import List

from sqlalchemy.exc import SQLAlchemyError

from ..diabetes.services.db import Reminder, SessionLocal, run_db
from ..schemas.reminders import ReminderSchema


async def list_reminders(telegram_id: int) -> List[Reminder]:
    def _list(session):
        return session.query(Reminder).filter_by(telegram_id=telegram_id).all()

    return await run_db(_list, sessionmaker=SessionLocal)


async def save_reminder(data: ReminderSchema) -> int:
    def _save(session):
        if data.id is not None:
            rem = session.get(Reminder, data.id)
            if rem is None or rem.telegram_id != data.telegram_id:
                raise SQLAlchemyError("not found")
        else:
            rem = Reminder(telegram_id=data.telegram_id)
            session.add(rem)
        if data.org_id is not None:
            rem.org_id = data.org_id
        rem.type = data.type
        rem.time = data.time
        rem.interval_hours = data.interval_hours
        rem.minutes_after = data.minutes_after
        rem.is_enabled = data.is_enabled
        session.commit()
        session.refresh(rem)
        return rem.id

    return await run_db(_save, sessionmaker=SessionLocal)
