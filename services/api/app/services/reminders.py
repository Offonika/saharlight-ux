from __future__ import annotations

from typing import cast

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..diabetes.services.db import Reminder, SessionLocal, User, run_db
from ..diabetes.services.repository import commit
from ..schemas.reminders import ReminderSchema
from ..types import SessionProtocol


async def list_reminders(telegram_id: int) -> list[Reminder]:
    def _list(session: SessionProtocol) -> list[Reminder]:
        if cast(User | None, session.get(User, telegram_id)) is None:
            return []
        return (
            cast(Session, session)
            .query(Reminder)
            .filter_by(telegram_id=telegram_id)
            .all()
        )

    return await run_db(_list, sessionmaker=SessionLocal)


async def save_reminder(data: ReminderSchema) -> int:
    def _save(session: SessionProtocol) -> int:
        if data.id is not None:
            rem = cast(Reminder | None, session.get(Reminder, data.id))
            if rem is None or rem.telegram_id != data.telegramId:
                raise HTTPException(status_code=404, detail="reminder not found")
        else:
            rem = Reminder(telegram_id=data.telegramId)
            cast(Session, session).add(rem)
        if data.orgId is not None:
            rem.org_id = data.orgId
        rem.type = data.type
        rem.title = data.title
        rem.time = data.time
        rem.interval_hours = data.intervalHours
        rem.minutes_after = data.minutesAfter
        rem.is_enabled = data.isEnabled
        commit(cast(Session, session))
        cast(Session, session).refresh(rem)
        return cast(int, rem.id)

    return await run_db(_save, sessionmaker=SessionLocal)


async def delete_reminder(telegram_id: int, reminder_id: int) -> None:
    def _delete(session: SessionProtocol) -> None:
        rem = cast(Reminder | None, session.get(Reminder, reminder_id))
        if rem is None or rem.telegram_id != telegram_id:
            raise HTTPException(status_code=404, detail="reminder not found")
        session.delete(rem)
        commit(cast(Session, session))

    await run_db(_delete, sessionmaker=SessionLocal)
