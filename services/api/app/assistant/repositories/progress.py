from __future__ import annotations

from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy.orm import Session

from ...diabetes.models_learning import LearningProgress
from ...diabetes.services.db import SessionLocal, run_db
from ...diabetes.services.repository import commit
from ...types import SessionProtocol

__all__ = ["get_progress", "upsert_progress"]


async def get_progress(user_id: int, plan_id: int) -> LearningProgress | None:
    """Return progress for a user and plan if present."""

    def _get(session: SessionProtocol) -> LearningProgress | None:
        stmt = sa.select(LearningProgress).where(
            LearningProgress.user_id == user_id,
            LearningProgress.plan_id == plan_id,
        )
        sess = cast(Session, session)
        return cast(LearningProgress | None, sess.scalar(stmt))

    return await run_db(_get, sessionmaker=SessionLocal)


async def upsert_progress(user_id: int, plan_id: int, progress_json: dict[str, Any]) -> LearningProgress:
    """Insert or update learning progress for a user and plan."""

    def _upsert(session: SessionProtocol) -> LearningProgress:
        stmt = sa.select(LearningProgress).where(
            LearningProgress.user_id == user_id,
            LearningProgress.plan_id == plan_id,
        )
        sess = cast(Session, session)
        progress = cast(LearningProgress | None, sess.scalar(stmt))
        if progress is None:
            progress = LearningProgress(user_id=user_id, plan_id=plan_id, progress_json=progress_json)
            sess.add(progress)
        else:
            progress.progress_json = progress_json
        commit(sess)
        sess.refresh(progress)
        return progress

    return await run_db(_upsert, sessionmaker=SessionLocal)
