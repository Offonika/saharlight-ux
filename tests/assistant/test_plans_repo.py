import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.services import db
from services.api.app.assistant.repositories import plans


@pytest.fixture()
def session_local(monkeypatch: pytest.MonkeyPatch) -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(plans, "SessionLocal", session_local)
    return session_local


@pytest.mark.asyncio
async def test_create_and_get(session_local: sessionmaker[Session]) -> None:
    plan_id = await plans.create_plan(1, version=1, plan_json={"a": 1})
    assert plan_id > 0
    fetched = await plans.get_plan(plan_id)
    assert fetched is not None
    assert fetched.user_id == 1
    assert fetched.version == 1
    assert fetched.plan_json == {"a": 1}


@pytest.mark.asyncio
async def test_get_active(session_local: sessionmaker[Session]) -> None:
    await plans.create_plan(1, version=1, plan_json={}, is_active=False)
    active_id = await plans.create_plan(1, version=2, plan_json={})
    active = await plans.get_active_plan(1)
    assert active is not None
    assert active.id == active_id


@pytest.mark.asyncio
async def test_update_and_delete(session_local: sessionmaker[Session]) -> None:
    plan_id = await plans.create_plan(2, version=1, plan_json={"x": 1})
    await plans.update_plan(plan_id, plan_json={"x": 2}, is_active=False)
    updated = await plans.get_plan(plan_id)
    assert updated is not None
    assert updated.plan_json == {"x": 2}
    assert updated.is_active is False
    await plans.delete_plan(plan_id)
    assert await plans.get_plan(plan_id) is None
