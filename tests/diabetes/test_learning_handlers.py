import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.config import settings
from services.api.app.diabetes import learning_handlers as dynamic_handlers
from services.api.app.diabetes.handlers import learning_handlers as legacy_handlers
from services.api.app.diabetes.learning_fixtures import load_lessons
from services.api.app.diabetes.services import db


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.replies: list[str] = []

    async def reply_text(
        self, text: str, **kwargs: Any
    ) -> None:  # pragma: no cover - helper
        self.replies.append(text)


class DummyCallback:
    def __init__(self, message: DummyMessage, data: str) -> None:
        self.message = message
        self.data = data
        self.answered = False

    async def answer(self) -> None:  # pragma: no cover - helper
        self.answered = True


@pytest.mark.asyncio
async def test_learn_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", False)
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message, effective_user=None))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    await legacy_handlers.learn_command(update, context)
    assert message.replies == ["🚫 Обучение недоступно."]


def setup_db() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)
    return SessionLocal


@pytest.mark.asyncio
async def test_learn_enabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)
    monkeypatch.setattr(settings, "learning_command_model", "super-model")
    sample = [
        {
            "title": "Sample",
            "steps": ["s1"],
            "quiz": [{"question": "q1", "options": ["1", "2", "3"], "answer": 1}],
        }
    ]
    path = tmp_path / "lessons.json"
    path.write_text(json.dumps(sample), encoding="utf-8")
    SessionLocal = setup_db()
    await load_lessons(path, sessionmaker=SessionLocal)
    monkeypatch.setattr(legacy_handlers, "SessionLocal", SessionLocal)
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message, effective_user=None))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            user_data={
                "learning_onboarded": True,
                "learn_profile_overrides": {
                    "age_group": "adult",
                    "diabetes_type": "T1",
                    "learning_level": "novice",
                },
            }
        ),
    )
    await legacy_handlers.learn_command(update, context)
    assert "super-model" in message.replies[0]


@pytest.mark.asyncio
async def test_dynamic_learn_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", False)
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = SimpleNamespace(user_data={}, args=[])
    await dynamic_handlers.learn_command(update, context)
    assert message.replies == ["режим обучения отключён"]


@pytest.mark.asyncio
async def test_dynamic_lesson_command_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", False)
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = SimpleNamespace(user_data={}, args=["slug"])
    await dynamic_handlers.lesson_command(update, context)
    assert message.replies == ["режим обучения отключён"]


@pytest.mark.asyncio
async def test_dynamic_lesson_callback_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", False)
    message = DummyMessage()
    query = DummyCallback(message, "lesson:slug")
    update = cast(Update, SimpleNamespace(callback_query=query))
    context = SimpleNamespace(user_data={})
    await dynamic_handlers.lesson_callback(update, context)
    assert message.replies == ["режим обучения отключён"]
    assert query.answered is True


@pytest.mark.asyncio
async def test_dynamic_lesson_answer_handler_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", False)
    message = DummyMessage(text="ans")
    update = cast(Update, SimpleNamespace(message=message))
    context = SimpleNamespace(user_data={})
    await dynamic_handlers.lesson_answer_handler(update, context)
    assert message.replies == ["режим обучения отключён"]


@pytest.mark.asyncio
async def test_dynamic_exit_command_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", False)
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = SimpleNamespace(user_data={})
    await dynamic_handlers.exit_command(update, context)
    assert message.replies == ["режим обучения отключён"]
