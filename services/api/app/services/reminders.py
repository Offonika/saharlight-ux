from __future__ import annotations


from datetime import datetime, timedelta, time as time_, timezone
from importlib import resources
from typing import Callable, cast

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..diabetes.services.db import Reminder, SessionLocal, User, run_db
from ..diabetes.services.repository import CommitError, commit
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
        reminders_ = session.query(Reminder).filter_by(telegram_id=telegram_id).all()
        sql = resources.files("services.api.app.diabetes.sql").joinpath(
            "reminders_stats.sql"
        ).read_text()
        since = datetime.now(timezone.utc) - timedelta(days=7)
        rows = session.execute(
            text(sql), {"telegram_id": telegram_id, "since": since}
        ).mappings()
        stats = {row["reminder_id"]: row for row in rows}
        for rem in reminders_:
            st = stats.get(rem.id)
            last = st["last_fired_at"] if st else None
            if isinstance(last, str):
                last = datetime.fromisoformat(last)
            setattr(rem, "last_fired_at", last)
            setattr(rem, "fires7d", st["fires7d"] if st else 0)
        return reminders_

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
        rem.interval_minutes = data.intervalMinutes
        rem.set_interval_hours_if_needed(data.intervalHours)
        rem.minutes_after = data.minutesAfter
        rem.is_enabled = data.isEnabled
        try:
            commit(cast(Session, session))
        except CommitError:
            raise HTTPException(status_code=500, detail="db commit failed")
        cast(Session, session).refresh(rem)
        assert rem.id is not None
        return rem.id

    try:
        return cast(
            int,
            await run_db(
                cast(Callable[[Session], int], _save), sessionmaker=SessionLocal
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


async def delete_reminder(telegram_id: int, reminder_id: int) -> None:
    def _delete(session: SessionProtocol) -> None:
        rem = cast(Reminder | None, session.get(Reminder, reminder_id))
        if rem is None or rem.telegram_id != telegram_id:
            raise HTTPException(status_code=404, detail="reminder not found")
        session.delete(rem)
        try:
            commit(cast(Session, session))
        except CommitError:
            raise HTTPException(status_code=500, detail="db commit failed")

    await run_db(cast(Callable[[Session], None], _delete), sessionmaker=SessionLocal)
