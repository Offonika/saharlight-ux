from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app import config
from services.api.app.diabetes import learning_handlers


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)


@pytest.mark.asyncio
async def test_lesson_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "get_settings", lambda: SimpleNamespace(learning_mode_enabled=False))
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    await learning_handlers.lesson_command(update, context)
    assert message.replies == ["режим выключен"]


@pytest.mark.asyncio
async def test_quiz_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "get_settings", lambda: SimpleNamespace(learning_mode_enabled=False))
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    await learning_handlers.quiz_command(update, context)
    assert message.replies == ["режим выключен"]


@pytest.mark.asyncio
async def test_progress_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "get_settings", lambda: SimpleNamespace(learning_mode_enabled=False))
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    await learning_handlers.progress_command(update, context)
    assert message.replies == ["режим выключен"]


@pytest.mark.asyncio
async def test_exit_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "get_settings", lambda: SimpleNamespace(learning_mode_enabled=True))
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    await learning_handlers.exit_command(update, context)
    assert message.replies == ["🚪 Выход из режима обучения."]
