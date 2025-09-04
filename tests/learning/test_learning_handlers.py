from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.diabetes.handlers import learning_handlers
from services.api.app.diabetes.models_learning import Lesson, LessonProgress
from services.api.app.diabetes.services import db


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)


@pytest.mark.asyncio()
async def test_progress_no_data() -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.SessionLocal.configure(bind=engine)
    db.Base.metadata.create_all(bind=engine)
    try:
        message = DummyMessage()
        user = SimpleNamespace(id=1)
        update = cast(Update, SimpleNamespace(effective_message=message, effective_user=user))
        context = cast(
            CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
            SimpleNamespace(),
        )
        await learning_handlers.progress_command(update, context)
        assert "/learn" in message.replies[0]
    finally:
        db.dispose_engine(engine)


@pytest.mark.asyncio()
async def test_progress_card() -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.SessionLocal.configure(bind=engine)
    db.Base.metadata.create_all(bind=engine)
    try:
        with db.SessionLocal() as session:
            session.add(db.User(telegram_id=1, thread_id="t1"))
            lesson = Lesson(slug="slug", title="Title", content="c", is_active=True)
            session.add(lesson)
            session.flush()
            session.add(
                LessonProgress(
                    user_id=1,
                    lesson_id=lesson.id,
                    current_step=3,
                    completed=True,
                    quiz_score=80,
                )
            )
            session.commit()

        message = DummyMessage()
        user = SimpleNamespace(id=1)
        update = cast(Update, SimpleNamespace(effective_message=message, effective_user=user))
        context = cast(
            CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
            SimpleNamespace(),
        )
        await learning_handlers.progress_command(update, context)
        reply = message.replies[0]
        assert "Title" in reply
        assert "current_step: 3" in reply
        assert "completed: True" in reply
        assert "quiz_score: 80" in reply
    finally:
        db.dispose_engine(engine)
