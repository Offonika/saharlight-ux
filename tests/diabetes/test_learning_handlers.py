from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from services.api.app.config import settings
from services.api.app.diabetes.handlers import learning_handlers
from services.api.app.diabetes.learning_fixtures import load_lessons
from services.api.app.diabetes.models_learning import Lesson, LessonProgress
from services.api.app.diabetes.services import db
from services.api.app.diabetes.utils.ui import menu_keyboard


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []
        self.from_user = SimpleNamespace(id=1)

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_learn_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_enabled", False)
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    await learning_handlers.learn_command(update, context)
    assert message.replies == ["🚫 Обучение недоступно."]


@pytest.mark.asyncio
async def test_learn_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_enabled", True)
    monkeypatch.setattr(settings, "learning_command_model", "super-model")
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    await learning_handlers.learn_command(update, context)
    assert "super-model" in message.replies[0]


@pytest.mark.asyncio
async def test_exit_command_clears_state_and_marks_progress() -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.SessionLocal.configure(bind=engine)
    db.Base.metadata.create_all(bind=engine)
    await load_lessons(
        "services/api/app/diabetes/content/lessons_v0.json",
        sessionmaker=db.SessionLocal,
    )
    with db.SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id="t1"))
        lesson = session.query(Lesson).first()
        assert lesson is not None
        lesson_id = lesson.id
        session.add(LessonProgress(user_id=1, lesson_id=lesson_id, completed=False))
        session.commit()

    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"lesson_id": lesson_id, "foo": "bar"}),
    )

    await learning_handlers.exit_command(update, context)

    assert message.replies == ["✅ Учебный режим завершён."]
    assert message.kwargs[0]["reply_markup"].keyboard == menu_keyboard().keyboard
    assert context.user_data is not None
    assert "lesson_id" not in context.user_data
    assert context.user_data.get("foo") == "bar"

    with db.SessionLocal() as session:
        progress = (
            session.query(LessonProgress)
            .filter_by(user_id=1, lesson_id=lesson_id)
            .one()
        )
        assert progress.completed is True
