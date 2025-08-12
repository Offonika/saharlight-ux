from __future__ import annotations

from services.api.app.diabetes.services.db import Profile, SessionLocal, User, run_db
from services.api.app.schemas.profile import ProfileSchema


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
        if data.org_id is not None:
            profile.org_id = data.org_id
        profile.icr = data.icr
        profile.cf = data.cf
        profile.target_bg = data.target
        profile.low_threshold = data.low
        profile.high_threshold = data.high
        session.commit()

    await run_db(_save, sessionmaker=SessionLocal)
