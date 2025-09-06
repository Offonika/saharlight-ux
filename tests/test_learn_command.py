from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.learning_handlers as handlers
from services.api.app.config import Settings
from services.api.app.diabetes.learning_fixtures import load_lessons
from services.api.app.diabetes.services import db


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


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
async def test_learn_command_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """When flag is disabled the command should warn the user."""

    monkeypatch.setattr(handlers, "settings", Settings(_env_file=None))
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await handlers.learn_command(update, context)

    assert message.replies == ["🚫 Обучение недоступно."]


@pytest.mark.asyncio
async def test_learn_command_no_lessons(monkeypatch: pytest.MonkeyPatch) -> None:
    """When no lessons loaded the user gets a hint."""

    SessionLocal = setup_db()
    monkeypatch.setattr(handlers, "SessionLocal", SessionLocal)
    monkeypatch.setattr(
        handlers,
        "settings",
        Settings(LEARNING_ENABLED="1", LEARNING_COMMAND_MODEL="m", _env_file=None),
    )
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await handlers.learn_command(update, context)

    assert message.replies == ["Уроки не найдены. Загрузите уроки: make load-lessons"]


@pytest.mark.asyncio
async def test_learn_command_lists_lessons(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """After loading fixtures /learn should show at least one button."""

    sample = [
        {
            "title": "Sample",
            "steps": ["a", "b", "c"],
            "quiz": [
                {"question": "q1", "options": ["1", "2", "3"], "answer": 1},
                {"question": "q2", "options": ["1", "2", "3"], "answer": 2},
                {"question": "q3", "options": ["1", "2", "3"], "answer": 0},
            ],
        }
    ]
    path = tmp_path / "lessons.json"
    path.write_text(json.dumps(sample), encoding="utf-8")

    SessionLocal = setup_db()
    await load_lessons(path, sessionmaker=SessionLocal)

    monkeypatch.setattr(handlers, "SessionLocal", SessionLocal)
    monkeypatch.setattr(
        handlers,
        "settings",
        Settings(LEARNING_ENABLED="1", LEARNING_COMMAND_MODEL="m", _env_file=None),
    )
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await handlers.learn_command(update, context)

    assert message.replies[0].startswith("🤖 Учебный режим активирован.")
    keyboard = message.kwargs[0].get("reply_markup")
    assert keyboard is not None
    assert keyboard.keyboard
