from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.services import db

from services.api.app.assistant.repositories.logs import (
    add_lesson_log,
    cleanup_old_logs,
    get_lesson_logs,
)
from services.api.app.assistant.models import LessonLog  # noqa: F401


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
        session.commit()


@pytest.mark.asyncio
async def test_add_and_get_logs(setup_db: None) -> None:
    await add_lesson_log(1, 42, 0, 1, "assistant", "a")
    await add_lesson_log(1, 42, 0, 1, "user", "b")
    logs = await get_lesson_logs(1, 42)
    assert [log.role for log in logs] == ["assistant", "user"]
    assert isinstance(logs[0].created_at, type(logs[1].created_at))


@pytest.mark.asyncio
async def test_cleanup_old_logs(setup_db: None) -> None:
    old = datetime.now(timezone.utc) - timedelta(days=15)
    now = datetime.now(timezone.utc)
    with db.SessionLocal() as session:
        session.add(
            LessonLog(
                user_id=1,
                plan_id=42,
                module_idx=0,
                step_idx=1,
                role="assistant",
                content="a",
                created_at=old,
            )
        )
        session.add(
            LessonLog(
                user_id=1,
                plan_id=42,
                module_idx=0,
                step_idx=2,
                role="assistant",
                content="b",
                created_at=now,
            )
        )
        session.commit()

    await cleanup_old_logs(ttl=timedelta(days=14))

    with db.SessionLocal() as session:
        logs = session.query(LessonLog).all()
        assert len(logs) == 1
        assert logs[0].step_idx == 2


def test_lesson_logs_index(setup_db: None) -> None:
    with db.SessionLocal() as session:
        engine = session.get_bind()
        indexes = {idx["name"] for idx in inspect(engine).get_indexes("lesson_logs")}
    assert "ix_lesson_logs_user_plan" in indexes
    assert "ix_lesson_logs_user_id" not in indexes
    assert "ix_lesson_logs_plan_id" not in indexes
