import logging
from typing import cast

from sqlalchemy.orm import Session

from .db import Profile, SessionLocal, User, run_db
from .repository import CommitError, commit

logger = logging.getLogger(__name__)

__all__ = ["save_timezone"]


async def save_timezone(telegram_id: int, tz: str, auto: bool) -> None:
    """Persist user's timezone preferences.

    Ensures that both :class:`~services.api.app.diabetes.services.db.User` and
    :class:`~services.api.app.diabetes.services.db.Profile` exist for the given
    ``telegram_id`` and updates the timezone fields.
    """

    def _save(session: Session) -> None:
        user = cast(User | None, session.get(User, telegram_id))
        if user is None:
            user = User(telegram_id=telegram_id, thread_id="api")
            session.add(user)
        profile = cast(Profile | None, session.get(Profile, telegram_id))
        if profile is None:
            profile = Profile(telegram_id=telegram_id)
            session.add(profile)
        profile.timezone = tz
        profile.timezone_auto = auto
        try:
            commit(session)
        except CommitError:
            logger.exception("Failed to commit timezone for %s", telegram_id)
            raise

    await run_db(_save, sessionmaker=SessionLocal)
