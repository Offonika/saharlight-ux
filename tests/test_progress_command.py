from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.learning_handlers as handlers
from services.api.app.config import settings
from services.api.app.diabetes.services import db
from services.api.app.diabetes.models_learning import Lesson, LessonProgress
from services.api.app.ui.keyboard import LEARN_BUTTON_TEXT


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(self, text: str) -> None:  # pragma: no cover - simple capture
        self.replies.append(text)


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
async def test_progress_command_no_progress(monkeypatch: pytest.MonkeyPatch) -> None:
    settings.learning_mode_enabled = True
    settings.learning_content_mode = "static"
    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    with db.SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id="t1"))
        session.commit()

    await handlers.progress_command(update, context)

    assert message.replies == [
        f"Вы ещё не начали обучение. Нажмите кнопку {LEARN_BUTTON_TEXT} или команду /learn, чтобы начать."
    ]


@pytest.mark.asyncio
async def test_progress_command_with_progress() -> None:
    settings.learning_mode_enabled = True
    settings.learning_content_mode = "static"
    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    with db.SessionLocal() as session:
        user = db.User(telegram_id=1, thread_id="t1")
        lesson = Lesson(slug="intro", title="Intro", content="c")
        session.add_all([user, lesson])
        session.commit()
        assert session.query(Lesson).filter_by(slug="intro").one().id == lesson.id
        progress = LessonProgress(
            user_id=user.telegram_id,
            lesson_id=lesson.id,
            current_step=2,
            completed=False,
            quiz_score=50,
        )
        session.add(progress)
        session.commit()

    await handlers.progress_command(update, context)

    assert message.replies
    text = message.replies[0]
    assert "Intro" in text
    assert "Шаг: 2" in text
    assert "Завершено: нет" in text
    assert "Баллы викторины: 50" in text
