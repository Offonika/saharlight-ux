from __future__ import annotations

from typing import List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..diabetes.services.db import Reminder, SessionLocal, User, run_db
from ..schemas.reminders import ReminderSchema


async def list_reminders(telegram_id: int) -> List[Reminder]:
    def _list(session: Session) -> List[Reminder]:
        if session.get(User, telegram_id) is None:
            return []
        return session.query(Reminder).filter_by(telegram_id=telegram_id).all()

    return await run_db(_list, sessionmaker=SessionLocal)


async def save_reminder(data: ReminderSchema) -> int:
    def _save(session: Session) -> int:
        if data.id is not None:
            rem = session.get(Reminder, data.id)
            if rem is None or rem.telegram_id != data.telegramId:
                raise HTTPException(status_code=404, detail="reminder not found")
        else:
            rem = Reminder(telegram_id=data.telegramId)
            session.add(rem)
        if data.orgId is not None:
            rem.org_id = data.orgId
        rem.type = data.type
        rem.time = data.time
        rem.interval_hours = data.intervalHours
        rem.minutes_after = data.minutesAfter
        rem.is_enabled = data.isEnabled
        session.commit()
        session.refresh(rem)
        return rem.id

    return await run_db(_save, sessionmaker=SessionLocal)


async def delete_reminder(telegram_id: int, reminder_id: int) -> None:
    def _delete(session: Session) -> None:
        rem = session.get(Reminder, reminder_id)
        if rem is None or rem.telegram_id != telegram_id:
            raise HTTPException(status_code=404, detail="reminder not found")
        session.delete(rem)
        session.commit()

    await run_db(_delete, sessionmaker=SessionLocal)
