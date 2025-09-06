from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.dynamic_tutor import log_lesson_turn
from services.api.app.diabetes.models_learning import LessonLog
from services.api.app.diabetes.services import db


@pytest.fixture()
def setup_db() -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.SessionLocal.configure(bind=engine)
    db.Base.metadata.create_all(bind=engine)


@pytest.mark.asyncio
async def test_log_creation_and_retrieval(setup_db: None) -> None:
    await log_lesson_turn(1, "topic", "assistant", 1, "text")
    await asyncio.sleep(0)
    with db.SessionLocal() as session:
        logs = session.query(LessonLog).filter_by(telegram_id=1).all()
        assert len(logs) == 1
        assert logs[0].content == "text"
