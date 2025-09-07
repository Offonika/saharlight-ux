from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from services.api.app.config import settings
from services.api.app.diabetes.services import db
from services.api.app.assistant.models import LessonLog
from services.api.app.assistant.repositories.logs import (
    add_lesson_log,
    get_lesson_logs,
    cleanup_lesson_logs,
)


@pytest.fixture()
def setup_db(monkeypatch: pytest.MonkeyPatch) -> None:
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
    monkeypatch.setattr(settings, "lesson_logs_enabled", True)


@pytest.mark.asyncio
async def test_add_and_get_logs(setup_db: None) -> None:
    await add_lesson_log(1, 2, 0, 1, "assistant", "hi")
    await add_lesson_log(1, 2, 0, 1, "user", "answer")
    logs = await get_lesson_logs(1, 2)
    assert [log.role for log in logs] == ["assistant", "user"]
    assert logs[0].content == "hi"
    assert logs[1].content == "answer"


@pytest.mark.asyncio
async def test_disabled_flag(monkeypatch: pytest.MonkeyPatch, setup_db: None) -> None:
    monkeypatch.setattr(settings, "lesson_logs_enabled", False)
    await add_lesson_log(1, 2, 0, 1, "assistant", "hi")
    assert await get_lesson_logs(1, 2) == []


@pytest.mark.asyncio
async def test_cleanup_old_logs(setup_db: None) -> None:
    old_time = datetime.now(timezone.utc) - timedelta(days=30)
    with db.SessionLocal() as session:
        session.add(
            LessonLog(
                user_id=1,
                plan_id=2,
                module_idx=0,
                step_idx=1,
                role="assistant",
                content="old",
                created_at=old_time,
            )
        )
        session.commit()
    await add_lesson_log(1, 2, 0, 1, "assistant", "new")
    removed = await cleanup_lesson_logs(max_age_days=14)
    assert removed == 1
    logs = await get_lesson_logs(1, 2)
    assert len(logs) == 1
    assert logs[0].content == "new"
