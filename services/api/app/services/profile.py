from __future__ import annotations

from fastapi import HTTPException
from typing import cast

from sqlalchemy.orm import Session

from ..diabetes.services.db import Profile, SessionLocal, User, run_db
from ..diabetes.services.repository import CommitError, commit
from ..schemas.profile import ProfileSchema
from ..types import SessionProtocol


async def set_timezone(telegram_id: int, tz: str) -> None:
    def _save(session: SessionProtocol) -> None:
        user = cast(User | None, session.get(User, telegram_id))
        if user is None:
            user = User(telegram_id=telegram_id, thread_id="api", timezone=tz)
            cast(Session, session).add(user)
        else:
            user.timezone = tz
        try:
            commit(cast(Session, session))
        except CommitError:
            raise HTTPException(status_code=500, detail="db commit failed")

    await run_db(_save, sessionmaker=SessionLocal)


def _validate_profile(data: ProfileSchema) -> None:
    """Validate business rules for a patient profile."""
    if (
        data.icr <= 0
        or data.cf <= 0
        or data.target <= 0
        or data.low <= 0
        or data.high <= 0
        or data.low >= data.high
    ):
        raise ValueError("invalid profile values")

    if not (data.low < data.target < data.high):
        raise ValueError("target must be between low and high")


async def save_profile(data: ProfileSchema) -> None:
    _validate_profile(data)

    def _save(session: SessionProtocol) -> None:
        profile = cast(Profile | None, session.get(Profile, data.telegramId))
        if profile is None:
            profile = Profile(telegram_id=data.telegramId)
            cast(Session, session).add(profile)
        if data.orgId is not None:
            profile.org_id = data.orgId
        profile.icr = data.icr
        profile.cf = data.cf
        profile.target_bg = data.target
        profile.low_threshold = data.low
        profile.high_threshold = data.high
        profile.sos_contact = data.sosContact or ""
        profile.sos_alerts_enabled = (
            data.sosAlertsEnabled if data.sosAlertsEnabled is not None else True
        )
        profile.quiet_start = data.quietStart
        profile.quiet_end = data.quietEnd
        try:
            commit(cast(Session, session))
        except CommitError:
            raise HTTPException(status_code=500, detail="db commit failed")

    await run_db(_save, sessionmaker=SessionLocal)


async def get_profile(telegram_id: int) -> Profile | None:
    def _get(session: SessionProtocol) -> Profile | None:
        return cast(Profile | None, session.get(Profile, telegram_id))

    return await run_db(_get, sessionmaker=SessionLocal)
