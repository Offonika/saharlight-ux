from __future__ import annotations

from fastapi import HTTPException
from typing import cast

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ..diabetes.services.db import Profile, SessionLocal, User, run_db
from ..diabetes.services.repository import CommitError, commit
from ..schemas.profile import ProfileSchema
from ..types import SessionProtocol


async def set_timezone(telegram_id: int, tz: str) -> None:  # pragma: no cover
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
    required = {
        "ratio": data.ratio,
        "target": data.target,
        "low": data.low,
        "high": data.high,
    }
    for name, value in required.items():
        if value is None:
            raise ValueError("field is required")  # pragma: no cover
        if value <= 0:
            raise ValueError(f"{name} must be greater than 0")  # pragma: no cover

    low = cast(float, data.low)
    high = cast(float, data.high)
    target = cast(float, data.target)

    if low >= high:
        raise ValueError("low must be less than high")  # pragma: no cover

    if not (low < target < high):
        raise ValueError("target must be between low and high")  # pragma: no cover

    # quiet times are validated by Pydantic; no additional checks required


async def save_profile(data: ProfileSchema) -> None:
    _validate_profile(data)

    def _save(session: SessionProtocol) -> None:
        user = cast(User | None, session.get(User, data.telegramId))
        if user is None:
            user = User(telegram_id=data.telegramId, thread_id="api")
            cast(Session, session).add(user)

        profile_data = {
            "telegram_id": data.telegramId,
            "org_id": data.orgId,
            "icr": data.ratio,
            "cf": data.ratio,
            "target_bg": data.target,
            "low_threshold": data.low,
            "high_threshold": data.high,
            "quiet_start": data.quietStart,
            "quiet_end": data.quietEnd,
            "sos_contact": data.sosContact or "",
            "sos_alerts_enabled": (
                data.sosAlertsEnabled if data.sosAlertsEnabled is not None else True
            ),
        }

        stmt = insert(Profile).values(**profile_data)
        update_values = {
            key: getattr(stmt.excluded, key)
            for key in profile_data.keys()
            if key != "telegram_id"
        }
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=[Profile.telegram_id],
                set_=update_values,
            )
        )

        try:
            commit(cast(Session, session))
        except CommitError:  # pragma: no cover
            raise HTTPException(status_code=500, detail="db commit failed")

    await run_db(_save, sessionmaker=SessionLocal)


async def get_profile(telegram_id: int) -> Profile | None:  # pragma: no cover
    def _get(session: SessionProtocol) -> Profile | None:
        return cast(Profile | None, session.get(Profile, telegram_id))

    return await run_db(_get, sessionmaker=SessionLocal)
