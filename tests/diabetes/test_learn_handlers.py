from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import CallbackContext

from services.api.app.config import settings
from services.api.app.diabetes.models_learning import Lesson, LessonProgress
from services.api.app.diabetes.services import db
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "learn_handlers",
    Path(__file__).resolve().parents[2]
    / "services/api/app/diabetes/handlers/learn_handlers.py",
)
assert spec and spec.loader
learn_handlers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(learn_handlers)  # type: ignore[misc]


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[tuple[str, object | None]] = []

    async def reply_text(self, text: str, reply_markup: object | None = None) -> None:
        self.replies.append((text, reply_markup))


@pytest.mark.asyncio
async def test_learn_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", False)
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    await learn_handlers.learn_command(update, context)
    assert message.replies == [("режим выключен", None)]


@pytest.mark.asyncio
async def test_learn_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)
    monkeypatch.setattr(settings, "learning_model_default", "super-model")
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    await learn_handlers.learn_command(update, context)
    assert "super-model" in message.replies[0][0]


@pytest.mark.asyncio
async def test_exit_command(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.SessionLocal.configure(bind=engine)
    db.Base.metadata.create_all(bind=engine)
    with db.SessionLocal() as session:
        lesson = Lesson(slug="intro", title="Intro", content="Basics")
        session.add_all([db.User(telegram_id=1, thread_id="t"), lesson])
        session.commit()
        progress = LessonProgress(user_id=1, lesson_id=lesson.id, completed=False)
        session.add(progress)
        session.commit()
        lesson_id = lesson.id
        lesson_slug = lesson.slug
    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(
            message=message,
            effective_message=message,
            effective_user=SimpleNamespace(id=1),
        ),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"lesson_id": lesson_id, "lesson_slug": lesson_slug}),
    )
    await learn_handlers.exit_command(update, context)
    assert context.user_data == {}
    text, markup = message.replies[0]
    assert "Урок завершён" in text
    assert isinstance(markup, ReplyKeyboardMarkup)
    with db.SessionLocal() as session:
        progress = (
            session.query(LessonProgress)
            .filter_by(user_id=1, lesson_id=lesson_id)
            .one()
        )
        assert progress.completed is True
