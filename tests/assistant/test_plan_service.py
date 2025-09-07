from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from services.api.app.assistant.models import Plan
from services.api.app.assistant.services.plan_service import (
    create_plan,
    deactivate_plan,
    get_active_plan,
)
from services.api.app.diabetes.services import db


@pytest.mark.asyncio
async def test_create_and_get_plan(in_memory_db) -> None:
    assert await get_active_plan(1) is None

    plan = await create_plan(1, "first")
    assert plan.id is not None
    fetched = await get_active_plan(1)
    assert fetched and fetched.id == plan.id


@pytest.mark.asyncio
async def test_create_replaces_active(in_memory_db) -> None:
    first = await create_plan(1, "first")
    second = await create_plan(1, "second")
    assert second.id != first.id

    def _get(session):
        return session.get(Plan, first.id)

    stored_first = await db.run_db(_get, sessionmaker=db.SessionLocal)
    assert stored_first is not None and not stored_first.active

    active = await get_active_plan(1)
    assert active and active.id == second.id


@pytest.mark.asyncio
async def test_deactivate_plan(in_memory_db) -> None:
    plan = await create_plan(1, "p")
    await deactivate_plan(plan.id)
    assert await get_active_plan(1) is None


@pytest.mark.asyncio
async def test_unique_active_constraint(in_memory_db) -> None:
    await create_plan(1, "p1")

    def _insert(session):
        session.add(Plan(user_id=1, content="p2", active=True))
        session.commit()

    with pytest.raises(IntegrityError):
        await db.run_db(_insert, sessionmaker=db.SessionLocal)
