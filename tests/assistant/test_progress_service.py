from __future__ import annotations

import asyncio
from datetime import datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.assistant.services import progress_service
from services.api.app.diabetes.models_learning import LearningPlan
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
    monkeypatch.setattr(progress_service, "SessionLocal", session_local)
    return session_local


@pytest.mark.asyncio()
async def test_get_progress_none(session_local: sessionmaker[Session]) -> None:
    with session_local() as session:
        session.add(db.User(telegram_id=1, thread_id=""))
        plan = LearningPlan(user_id=1, version=1, plan_json=[])
        session.add(plan)
        session.commit()
        plan_id = plan.id

    result = await progress_service.get_progress(1, plan_id)
    assert result is None


@pytest.mark.asyncio()
async def test_upsert_updates_timestamp(session_local: sessionmaker[Session]) -> None:
    with session_local() as session:
        session.add(db.User(telegram_id=1, thread_id=""))
        plan = LearningPlan(user_id=1, version=1, plan_json=[])
        session.add(plan)
        session.commit()
        plan_id = plan.id

    await progress_service.upsert_progress(1, plan_id, {"step": 1})
    progress = await progress_service.get_progress(1, plan_id)
    assert progress is not None

    old_ts = datetime(2000, 1, 1)
    with session_local() as session:
        stored = session.get(progress_service.LearningProgress, progress.id)
        assert stored is not None
        stored.updated_at = old_ts
        session.commit()

    await progress_service.upsert_progress(1, plan_id, {"step": 2})
    progress2 = await progress_service.get_progress(1, plan_id)
    assert progress2 is not None
    assert progress2.progress_json == {"step": 2}
    assert progress2.updated_at > old_ts


@pytest.mark.asyncio()
async def test_upsert_progress_concurrent(session_local: sessionmaker[Session]) -> None:
    with session_local() as session:
        session.add(db.User(telegram_id=1, thread_id=""))
        plan = LearningPlan(user_id=1, version=1, plan_json=[])
        session.add(plan)
        session.commit()
        plan_id = plan.id

    async def upsert(step: int) -> None:
        if step == 2:
            await asyncio.sleep(0)
        await progress_service.upsert_progress(1, plan_id, {"step": step})

    await asyncio.gather(upsert(1), upsert(2))
    progress = await progress_service.get_progress(1, plan_id)
    assert progress is not None
    assert progress.progress_json == {"step": 2}

