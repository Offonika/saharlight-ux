from __future__ import annotations

from typing import List

from diabetes.services.db import (
    Profile,
    Reminder,
    SessionLocal,
    User,
    init_db,
    run_db,
)
__all__ = ["init_db", "set_timezone", "save_profile", "list_reminders", "save_reminder"]
from sqlalchemy.exc import SQLAlchemyError

from .schemas import ProfileSchema, ReminderSchema


async def set_timezone(telegram_id: int, tz: str) -> None:
    def _save(session):
        user = session.get(User, telegram_id)
        if user is None:
            user = User(telegram_id=telegram_id, thread_id="api", timezone=tz)
            session.add(user)
        else:
            user.timezone = tz
        session.commit()

    await run_db(_save, sessionmaker=SessionLocal)


async def save_profile(data: ProfileSchema) -> None:
    def _save(session):
        profile = session.get(Profile, data.telegram_id)
        if profile is None:
            profile = Profile(telegram_id=data.telegram_id)
            session.add(profile)
        profile.icr = data.icr
        profile.cf = data.cf
        profile.target_bg = data.target
        profile.low_threshold = data.low
        profile.high_threshold = data.high
        session.commit()

    await run_db(_save, sessionmaker=SessionLocal)


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
        rem.type = data.type
        rem.time = data.time
        rem.interval_hours = data.interval_hours
        rem.minutes_after = data.minutes_after
        rem.is_enabled = data.is_enabled
        session.commit()
        session.refresh(rem)
        return rem.id

    return await run_db(_save, sessionmaker=SessionLocal)
