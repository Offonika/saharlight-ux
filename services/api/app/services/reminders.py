from __future__ import annotations


from typing import Callable, cast


from datetime import time as time_

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..diabetes.services.db import Reminder, SessionLocal, User, run_db
from ..diabetes.services.repository import commit
from ..schemas.reminders import ReminderSchema
from ..types import SessionProtocol


def _default_title(rem_type: str, rem_time: time_ | None) -> str | None:
    if rem_time is not None and rem_type in {"sugar", "meal"}:
        hour = rem_time.hour
        if 5 <= hour < 12:
            return "Morning"
        if 12 <= hour < 17:
            return "Lunch"
        if 17 <= hour < 22:
            return "Evening"
        return "Night"
    if rem_time is not None:
        return rem_time.strftime("%H:%M")
    return None


async def list_reminders(telegram_id: int) -> list[Reminder]:
    def _list(session: Session) -> list[Reminder]:
        if cast(User | None, session.get(User, telegram_id)) is None:
            return []
        return session.query(Reminder).filter_by(telegram_id=telegram_id).all()

    return await run_db(_list, sessionmaker=SessionLocal)


async def save_reminder(data: ReminderSchema) -> int:
    def _save(session: SessionProtocol) -> int:
        rem: Reminder
        if data.id is not None:
            existing = cast(Reminder | None, session.get(Reminder, data.id))
            if existing is None or existing.telegram_id != data.telegramId:
                raise HTTPException(status_code=404, detail="reminder not found")
            rem = existing
        else:
            rem = Reminder(telegram_id=data.telegramId)
            cast(Session, session).add(rem)
        if data.orgId is not None:
            rem.org_id = data.orgId
        rem.type = data.type
        if data.title is not None:
            rem.title = data.title
        elif rem.title is None:
            rem.title = _default_title(data.type, data.time or rem.time)
        rem.time = data.time
        rem.interval_hours = data.intervalHours
        rem.minutes_after = data.minutesAfter
        rem.is_enabled = data.isEnabled
        commit(cast(Session, session))
        cast(Session, session).refresh(rem)
        assert rem.id is not None
        return rem.id

    return cast(
        int,
        await run_db(cast(Callable[[Session], int], _save), sessionmaker=SessionLocal),
    )


async def delete_reminder(telegram_id: int, reminder_id: int) -> None:
    def _delete(session: SessionProtocol) -> None:
        rem = cast(Reminder | None, session.get(Reminder, reminder_id))
        if rem is None or rem.telegram_id != telegram_id:
            raise HTTPException(status_code=404, detail="reminder not found")
        session.delete(rem)
        commit(cast(Session, session))

    await run_db(cast(Callable[[Session], None], _delete), sessionmaker=SessionLocal)
