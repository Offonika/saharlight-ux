from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.config import settings
from services.api.app.diabetes import learning_handlers


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.replies: list[str] = []
        self.text = text

    async def reply_text(self, text: str, **kwargs: Any) -> None:  # pragma: no cover - helper
        self.replies.append(text)


class DummyCallback:
    def __init__(self, message: DummyMessage, data: str = "lesson:slug") -> None:
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
    await learning_handlers.learn_command(update, context)
    assert message.replies == ["режим обучения отключён"]


@pytest.mark.asyncio
async def test_lesson_command_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", False)
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, args=[]),
    )
    await learning_handlers.lesson_command(update, context)
    assert message.replies == ["режим обучения отключён"]


@pytest.mark.asyncio
async def test_lesson_callback_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", False)
    msg = DummyMessage()
    query = DummyCallback(msg)
    update = cast(Update, SimpleNamespace(callback_query=query))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    await learning_handlers.lesson_callback(update, context)
    assert msg.replies == ["режим обучения отключён"]
    assert query.answered is True


@pytest.mark.asyncio
async def test_lesson_answer_handler_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", False)
    message = DummyMessage(text="ans")
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    await learning_handlers.lesson_answer_handler(update, context)
    assert message.replies == ["режим обучения отключён"]


@pytest.mark.asyncio
async def test_exit_command_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", False)
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    await learning_handlers.exit_command(update, context)
    assert message.replies == ["режим обучения отключён"]


@pytest.mark.asyncio
async def test_learn_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)

    async def fake_ensure_overrides(*args: object, **kwargs: object) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "ensure_overrides", fake_ensure_overrides)
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    await learning_handlers.learn_command(update, context)
    assert message.replies[:2] == ["Выберите тему:", "Доступные темы:"]
