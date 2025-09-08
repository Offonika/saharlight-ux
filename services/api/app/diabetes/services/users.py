from __future__ import annotations

import logging
from typing import cast

from sqlalchemy.orm import Session, sessionmaker

from .db import SessionLocal, User, run_db
from .repository import CommitError, commit

logger = logging.getLogger(__name__)

__all__ = ["ensure_user_exists"]


async def ensure_user_exists(
    user_id: int,
    thread_id: str = "",
    session_factory: sessionmaker[Session] | None = None,
) -> None:
    """Ensure that a user row exists for ``user_id``.

    If no :class:`~services.api.app.diabetes.services.db.User` exists with the given
    ``telegram_id``, a new one is inserted with ``thread_id``. Creation and duplicate
    situations are logged.
    """

    def _ensure(session: Session) -> None:
        user = cast(User | None, session.get(User, user_id))
        if user is not None:
            logger.info("User %s already exists", user_id)
            return
        session.add(User(telegram_id=user_id, thread_id=thread_id))
        try:
            commit(session)
        except CommitError:  # pragma: no cover - logging only
            existing = cast(User | None, session.get(User, user_id))
            if existing is not None:
                logger.info("User %s already exists (race)", user_id)
                return
            logger.exception("Failed to create user %s", user_id)
            raise
        logger.info("Created user %s", user_id)

    await run_db(_ensure, sessionmaker=session_factory or SessionLocal)
