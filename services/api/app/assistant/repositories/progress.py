from __future__ import annotations

import logging
import sqlalchemy as sa
from sqlalchemy.orm import Session

from services.api.app.assistant.models import LearningProgress
from services.api.app.diabetes.services.db import SessionLocal, run_db
from services.api.app.diabetes.services.repository import CommitError, commit

logger = logging.getLogger(__name__)

__all__ = ["get_progress", "upsert_progress"]


async def get_progress(user_id: int, plan_id: int) -> LearningProgress | None:
    """Fetch progress for ``user_id`` and ``plan_id`` if present."""

    def _get(session: Session) -> LearningProgress | None:
        return session.execute(
            sa.select(LearningProgress).filter_by(user_id=user_id, plan_id=plan_id)
        ).scalar_one_or_none()

    return await run_db(_get, sessionmaker=SessionLocal)


async def upsert_progress(user_id: int, plan_id: int, current_step: int) -> LearningProgress:
    """Create or update progress for ``user_id`` and ``plan_id``."""

    def _upsert(session: Session) -> LearningProgress:
        progress = session.execute(
            sa.select(LearningProgress).filter_by(user_id=user_id, plan_id=plan_id)
        ).scalar_one_or_none()
        if progress is None:
            progress = LearningProgress(
                user_id=user_id, plan_id=plan_id, current_step=current_step
            )
            session.add(progress)
        else:
            progress.current_step = current_step
        commit(session)
        session.refresh(progress)
        return progress

    try:
        return await run_db(_upsert, sessionmaker=SessionLocal)
    except CommitError:  # pragma: no cover - logging only
        logger.exception(
            "Failed to upsert learning progress for %s/%s", user_id, plan_id
        )
        raise
