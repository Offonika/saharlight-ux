from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.services import db
from services.api.app.assistant.repositories.logs import (
    add_lesson_log,
    get_lesson_logs,
    cleanup_lesson_logs,
)
from services.api.app.diabetes.models_learning import LessonLog, LearningPlan  # noqa: F401


@pytest.fixture()
def setup_db() -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.SessionLocal.configure(bind=engine)
    db.Base.metadata.create_all(bind=engine)
    with db.SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id="t"))
        session.add(LearningPlan(id=1, user_id=1, plan_json={}, is_active=True, version=1))
        session.commit()


@pytest.mark.asyncio
async def test_add_and_get_logs(setup_db: None) -> None:
    await add_lesson_log(1, 1, 0, 1, "assistant", "hi")
    await add_lesson_log(1, 1, 0, 1, "user", "answer")
    logs = await get_lesson_logs(1, 1, 0)
    assert [log.role for log in logs] == ["assistant", "user"]
    assert logs[0].content == "hi"
    assert logs[1].content == "answer"
    assert isinstance(logs[0].created_at, type(logs[1].created_at))


@pytest.mark.asyncio
async def test_cleanup_lesson_logs(setup_db: None) -> None:
    await add_lesson_log(1, 1, 0, 1, "assistant", "old")
    with db.SessionLocal() as session:
        session.query(LessonLog).update({LessonLog.created_at: datetime.now(tz=timezone.utc) - timedelta(days=30)})
        session.commit()
    await cleanup_lesson_logs(7)
    logs = await get_lesson_logs(1, 1, 0)
    assert not logs
