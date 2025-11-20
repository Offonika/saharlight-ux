from __future__ import annotations

import logging
from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy.orm import Session

from ...diabetes.models_learning import LearningPlan
from ...diabetes.services.db import SessionLocal, run_db
from ...diabetes.services.repository import commit
from ...types import SessionProtocol

logger = logging.getLogger(__name__)


async def get_active_plan(user_id: int) -> LearningPlan | None:
    """Return active learning plan for ``user_id`` if any."""

    def _get(session: SessionProtocol) -> LearningPlan | None:
        stmt = sa.select(LearningPlan).where(
            LearningPlan.user_id == user_id, LearningPlan.is_active.is_(True)
        )
        sess = cast(Session, session)
        return cast(LearningPlan | None, sess.scalar(stmt))

    return await run_db(_get, sessionmaker=SessionLocal)


async def create_plan(
    user_id: int,
    *,
    version: int,
    plan_json: dict[str, Any],
) -> int:
    """Create new active plan for ``user_id`` replacing previous one."""

    def _create(session: SessionProtocol) -> int:
        sess = cast(Session, session)
        sess.execute(
            sa.update(LearningPlan)
            .where(LearningPlan.user_id == user_id, LearningPlan.is_active.is_(True))
            .values(is_active=False)
        )
        plan = LearningPlan(
            user_id=user_id,
            version=version,
            plan_json=plan_json,
            is_active=True,
        )
        sess.add(plan)
        commit(sess)
        sess.refresh(plan)
        assert plan.id is not None
        return plan.id

    return cast(int, await run_db(_create, sessionmaker=SessionLocal))


async def deactivate_plan(plan_id: int) -> None:
    """Deactivate plan with ``plan_id`` if it exists."""

    def _deactivate(session: SessionProtocol) -> None:
        plan = cast(LearningPlan | None, session.get(LearningPlan, plan_id))
        if plan is None or not plan.is_active:
            return
        plan.is_active = False
        commit(cast(Session, session))

    await run_db(_deactivate, sessionmaker=SessionLocal)


__all__ = ["get_active_plan", "create_plan", "deactivate_plan"]
