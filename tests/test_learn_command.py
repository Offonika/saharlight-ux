from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.learning_handlers as handlers
from services.api.app.config import Settings


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(self, text: str) -> None:  # pragma: no cover - simple capture
        self.replies.append(text)


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
async def test_learn_command_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """With flag enabled the command should return training info."""

    monkeypatch.setattr(
        handlers,
        "settings",
        Settings(LEARNING_ENABLED="1", LEARNING_COMMAND_MODEL="test-model", _env_file=None),
    )
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await handlers.learn_command(update, context)

    assert message.replies == ["🤖 Учебный режим активирован. Модель: test-model"]
