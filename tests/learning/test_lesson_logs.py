from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.services import db
from datetime import datetime, timedelta, timezone

from services.api.app.assistant.repositories.logs import (
    add_lesson_log,
    get_lesson_logs,
    cleanup_old_logs,
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
    await add_lesson_log(1, 1, 0, 1, "assistant", "hi")
    await add_lesson_log(1, 1, 0, 1, "user", "answer")
    logs = await get_lesson_logs(1, 1)
    assert [log.role for log in logs] == ["assistant", "user"]
    assert logs[0].content == "hi"
    assert logs[1].content == "answer"
    assert isinstance(logs[0].created_at, type(logs[1].created_at))


@pytest.mark.asyncio
async def test_cleanup_old_logs(setup_db: None) -> None:
    old = datetime.now(timezone.utc) - timedelta(days=15)
    now = datetime.now(timezone.utc)
    with db.SessionLocal() as session:
        session.add(
            db.User(telegram_id=2, thread_id="t")
        )  # ensure user exists for completeness
        session.add(
            LessonLog(
                user_id=1,
                plan_id=1,
                module_idx=0,
                step_idx=1,
                role="assistant",
                content="old",
                created_at=old,
            )
        )
        session.add(
            LessonLog(
                user_id=1,
                plan_id=1,
                module_idx=0,
                step_idx=2,
                role="assistant",
                content="new",
                created_at=now,
            )
        )
        session.commit()

    await cleanup_old_logs(ttl=timedelta(days=14))

    with db.SessionLocal() as session:
        logs = session.query(LessonLog).all()
        assert len(logs) == 1
        assert logs[0].content == "new"
