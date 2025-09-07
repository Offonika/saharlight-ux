from __future__ import annotations

import logging

import sqlalchemy as sa
from sqlalchemy.orm import Session

from services.api.app.diabetes.services import db
from services.api.app.diabetes.services.repository import transactional

from ..models import Plan

logger = logging.getLogger(__name__)


async def get_active_plan(user_id: int) -> Plan | None:
    """Return active plan for given user if exists."""

    def _get(session: Session) -> Plan | None:
        stmt = sa.select(Plan).where(Plan.user_id == user_id, Plan.active)
        return session.execute(stmt).scalar_one_or_none()

    return await db.run_db(_get, sessionmaker=db.SessionLocal)


async def create_plan(user_id: int, content: str) -> Plan:
    """Create a new active plan for user.

    Deactivates existing active plan in a transaction to ensure only one active
    plan per user.
    """

    def _create(session: Session) -> Plan:
        with transactional(session):
            session.execute(
                sa.update(Plan)
                .where(Plan.user_id == user_id, Plan.active)
                .values(active=False)
            )
            plan = Plan(user_id=user_id, content=content, active=True)
            session.add(plan)
        session.refresh(plan)
        return plan

    return await db.run_db(_create, sessionmaker=db.SessionLocal)


async def deactivate_plan(plan_id: int) -> None:
    """Mark plan as inactive."""

    def _deactivate(session: Session) -> None:
        with transactional(session):
            session.execute(
                sa.update(Plan).where(Plan.id == plan_id).values(active=False)
            )

    await db.run_db(_deactivate, sessionmaker=db.SessionLocal)
