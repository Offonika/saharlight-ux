from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.learning_handlers as handlers
from services.api.app.diabetes.models_learning import Lesson, LessonProgress
from services.api.app.diabetes.services import db


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(
        self, text: str, **kwargs: Any
    ) -> None:  # pragma: no cover - capture only
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.fixture(autouse=True)
def setup_db() -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.SessionLocal.configure(bind=engine)
    db.Base.metadata.create_all(bind=engine)
    handlers.SessionLocal = db.SessionLocal  # type: ignore[assignment]
    yield
    db.dispose_engine(engine)


@pytest.mark.asyncio
async def test_exit_command_clears_state_and_marks_progress() -> None:
    message = DummyMessage()
    user_id = 1
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=user_id)),
    )
    user_data = {"lesson_id": 1, "lesson_slug": "intro", "lesson_step": 2}
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data),
    )

    with db.SessionLocal() as session:
        user = db.User(telegram_id=user_id, thread_id="t1")
        lesson = Lesson(slug="intro", title="Intro", content="c")
        session.add_all([user, lesson])
        session.commit()
        assert session.query(Lesson).filter_by(slug="intro").one().id == lesson.id
        progress = LessonProgress(
            user_id=user.telegram_id,
            lesson_id=lesson.id,
            current_step=1,
            completed=False,
        )
        session.add(progress)
        session.commit()

    await handlers.exit_command(update, context)

    assert message.replies and "заверш" in message.replies[0]
    assert message.kwargs and isinstance(
        message.kwargs[0].get("reply_markup"), ReplyKeyboardMarkup
    )
    assert user_data == {}
    with db.SessionLocal() as session:
        progress = session.query(LessonProgress).one()
        assert progress.completed is True
