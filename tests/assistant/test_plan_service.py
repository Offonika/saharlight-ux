from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.services import db
from services.api.app.assistant.services import plan_service
from services.api.app.assistant.repositories import plans
from services.api.app.diabetes.services.repository import CommitError


@pytest.fixture(autouse=True)
def setup_db(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(db, "SessionLocal", SessionLocal, raising=False)
    monkeypatch.setattr(plan_service, "SessionLocal", SessionLocal, raising=False)
    monkeypatch.setattr(plans, "SessionLocal", SessionLocal, raising=False)
    yield
    db.dispose_engine(engine)


@pytest.mark.asyncio
async def test_create_and_get_active() -> None:
    plan_id = await plan_service.create_plan(1, version=1, plan_json={"a": 1})
    active = await plan_service.get_active_plan(1)
    assert active is not None
    assert active.id == plan_id
    assert active.plan_json == {"a": 1}


@pytest.mark.asyncio
async def test_create_deactivates_previous() -> None:
    first = await plan_service.create_plan(1, version=1, plan_json={"a": 1})
    second = await plan_service.create_plan(1, version=2, plan_json={"b": 2})
    active = await plan_service.get_active_plan(1)
    assert active is not None and active.id == second
    first_plan = await plans.get_plan(first)
    second_plan = await plans.get_plan(second)
    assert first_plan is not None and first_plan.is_active is False
    assert second_plan is not None and second_plan.is_active is True


@pytest.mark.asyncio
async def test_deactivate_plan() -> None:
    plan_id = await plan_service.create_plan(1, version=1, plan_json={})
    await plan_service.deactivate_plan(plan_id)
    assert await plan_service.get_active_plan(1) is None


@pytest.mark.asyncio
async def test_unique_index_enforced() -> None:
    await plans.create_plan(1, version=1, plan_json={})
    with pytest.raises(CommitError):
        await plans.create_plan(1, version=2, plan_json={})
