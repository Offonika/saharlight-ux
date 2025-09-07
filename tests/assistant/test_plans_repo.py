from __future__ import annotations

import pytest  # required for pytest fixtures
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.assistant.repositories import plans
from services.api.app.diabetes.services import db


@pytest.fixture()
def session_local(monkeypatch: pytest.MonkeyPatch) -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection, connection_record) -> None:  # pragma: no cover - setup
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    session_local = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(plans, "SessionLocal", session_local)
    return session_local


@pytest.mark.asyncio
async def test_create_and_get(session_local: sessionmaker[Session]) -> None:
    with session_local() as session:
        session.add(db.User(telegram_id=1, thread_id=""))
        session.commit()
    plan_id = await plans.create_plan(1, version=1, plan_json={"a": 1})
    assert plan_id > 0
    fetched = await plans.get_plan(plan_id)
    assert fetched is not None
    assert fetched.user_id == 1
    assert fetched.version == 1
    assert fetched.plan_json == {"a": 1}


@pytest.mark.asyncio
async def test_get_active(session_local: sessionmaker[Session]) -> None:
    with session_local() as session:
        session.add(db.User(telegram_id=1, thread_id=""))
        session.commit()
    await plans.create_plan(1, version=1, plan_json={}, is_active=False)
    active_id = await plans.create_plan(1, version=2, plan_json={})
    active = await plans.get_active_plan(1)
    assert active is not None
    assert active.id == active_id


@pytest.mark.asyncio
async def test_update_delete_and_list(session_local: sessionmaker[Session]) -> None:
    with session_local() as session:
        session.add(db.User(telegram_id=2, thread_id=""))
        session.commit()
    plan_id1 = await plans.create_plan(2, version=1, plan_json={"x": 1})
    plan_id2 = await plans.create_plan(2, version=2, plan_json={"y": 1})
    await plans.update_plan(plan_id1, plan_json={"x": 2}, is_active=False)
    updated = await plans.get_plan(plan_id1)
    assert updated is not None
    assert updated.plan_json == {"x": 2}
    assert updated.is_active is False
    plans_list = await plans.list_plans(2)
    assert {p.id for p in plans_list} == {plan_id1, plan_id2}
    await plans.delete_plan(plan_id1)
    assert await plans.get_plan(plan_id1) is None
