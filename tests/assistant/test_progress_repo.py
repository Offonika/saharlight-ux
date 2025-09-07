from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.assistant.repositories import progress
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
    monkeypatch.setattr(progress, "SessionLocal", session_local)
    return session_local


@pytest.mark.asyncio
async def test_get_and_upsert(session_local: sessionmaker[Session]) -> None:
    with session_local() as session:
        session.add(db.User(telegram_id=1, thread_id=""))
        plan = LearningPlan(user_id=1, version=1, plan_json=[])
        session.add(plan)
        session.commit()
        plan_id = plan.id

    assert await progress.get_progress(1, plan_id) is None

    prog = await progress.upsert_progress(1, plan_id, {"step": 1})
    assert prog.progress_json == {"step": 1}

    fetched = await progress.get_progress(1, plan_id)
    assert fetched is not None
    assert fetched.progress_json == {"step": 1}

    prog2 = await progress.upsert_progress(1, plan_id, {"step": 2})
    assert prog2.progress_json == {"step": 2}
    fetched2 = await progress.get_progress(1, plan_id)
    assert fetched2 is not None
    assert fetched2.progress_json == {"step": 2}
