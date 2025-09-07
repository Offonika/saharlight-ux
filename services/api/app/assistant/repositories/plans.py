from __future__ import annotations

from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy.orm import Session

from ...diabetes.models_learning import LearningPlan
from ...diabetes.services.db import SessionLocal, run_db
from ...diabetes.services.repository import commit
from ...types import SessionProtocol


async def create_plan(
    user_id: int,
    version: int,
    plan_json: dict[str, Any],
    *,
    is_active: bool = True,
) -> int:
    def _create(session: SessionProtocol) -> int:
        sess = cast(Session, session)
        if is_active:
            stmt = (
                sa.update(LearningPlan)
                .where(
                    LearningPlan.user_id == user_id,
                    LearningPlan.is_active.is_(True),
                )
                .values(is_active=False)
            )
            sess.execute(stmt)
        plan = LearningPlan(
            user_id=user_id,
            version=version,
            plan_json=plan_json,
            is_active=is_active,
        )
        sess.add(plan)
        commit(sess)
        sess.refresh(plan)
        assert plan.id is not None
        return plan.id

    return cast(int, await run_db(_create, sessionmaker=SessionLocal))


async def get_plan(plan_id: int) -> LearningPlan | None:
    def _get(session: SessionProtocol) -> LearningPlan | None:
        return cast(LearningPlan | None, session.get(LearningPlan, plan_id))

    return await run_db(_get, sessionmaker=SessionLocal)


async def get_active_plan(user_id: int) -> LearningPlan | None:
    def _get(session: SessionProtocol) -> LearningPlan | None:
        stmt = sa.select(LearningPlan).where(
            LearningPlan.user_id == user_id, LearningPlan.is_active.is_(True)
        )
        sess = cast(Session, session)
        return cast(LearningPlan | None, sess.scalar(stmt))

    return await run_db(_get, sessionmaker=SessionLocal)


async def deactivate_plan(user_id: int, plan_id: int) -> None:
    def _deactivate(session: SessionProtocol) -> None:
        plan = cast(LearningPlan | None, session.get(LearningPlan, plan_id))
        if plan is None or plan.user_id != user_id:
            return
        plan.is_active = False
        commit(cast(Session, session))

    await run_db(_deactivate, sessionmaker=SessionLocal)


async def list_plans(user_id: int) -> list[LearningPlan]:
    def _list(session: SessionProtocol) -> list[LearningPlan]:
        stmt = sa.select(LearningPlan).where(LearningPlan.user_id == user_id)
        sess = cast(Session, session)
        return list(sess.scalars(stmt).all())

    return await run_db(_list, sessionmaker=SessionLocal)


async def update_plan(
    plan_id: int,
    *,
    plan_json: dict[str, Any] | None = None,
    is_active: bool | None = None,
    version: int | None = None,
) -> None:
    def _update(session: SessionProtocol) -> None:
        plan = cast(LearningPlan | None, session.get(LearningPlan, plan_id))
        if plan is None:
            return
        if plan_json is not None:
            plan.plan_json = plan_json
        if is_active is not None:
            plan.is_active = is_active
        if version is not None:
            plan.version = version
        commit(cast(Session, session))

    await run_db(_update, sessionmaker=SessionLocal)


async def delete_plan(plan_id: int) -> None:
    def _delete(session: SessionProtocol) -> None:
        plan = cast(LearningPlan | None, session.get(LearningPlan, plan_id))
        if plan is None:
            return
        session.delete(plan)
        commit(cast(Session, session))

    await run_db(_delete, sessionmaker=SessionLocal)
