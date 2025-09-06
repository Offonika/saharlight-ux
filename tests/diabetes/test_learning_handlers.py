from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.diabetes import learning_handlers


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:  # pragma: no cover - helper
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
    monkeypatch.setattr(learning_handlers.settings, "learning_mode_enabled", False)
    msg = DummyMessage()
    update = cast(Update, SimpleNamespace(message=msg))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    await learning_handlers.learn_command(update, context)
    assert msg.replies == ["режим обучения отключён"]


@pytest.mark.asyncio
async def test_learn_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_ensure_overrides(update: object, context: object) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "ensure_overrides", fake_ensure_overrides)
    monkeypatch.setattr(learning_handlers, "TOPICS", [("slug", "Topic")])
    monkeypatch.setattr(learning_handlers.settings, "learning_mode_enabled", True)

    msg = DummyMessage()
    update = cast(Update, SimpleNamespace(message=msg))
    context = SimpleNamespace(user_data={})
    await learning_handlers.learn_command(update, context)
    assert msg.replies == ["Выберите тему:"]


@pytest.mark.asyncio
async def test_lesson_command_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(learning_handlers.settings, "learning_mode_enabled", False)
    msg = DummyMessage()
    update = cast(Update, SimpleNamespace(message=msg))
    context = SimpleNamespace(user_data={}, args=["slug"])
    await learning_handlers.lesson_command(update, context)
    assert msg.replies == ["режим обучения отключён"]


@pytest.mark.asyncio
async def test_lesson_callback_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(learning_handlers.settings, "learning_mode_enabled", False)
    msg = DummyMessage()
    query = DummyCallback(msg, "lesson:slug")
    update = cast(Update, SimpleNamespace(callback_query=query))
    context = SimpleNamespace(user_data={})
    await learning_handlers.lesson_callback(update, context)
    assert query.answered
    assert msg.replies == ["режим обучения отключён"]


@pytest.mark.asyncio
async def test_lesson_answer_handler_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(learning_handlers.settings, "learning_mode_enabled", False)
    msg = DummyMessage(text="ans")
    update = cast(Update, SimpleNamespace(message=msg))
    context = SimpleNamespace(user_data={})
    await learning_handlers.lesson_answer_handler(update, context)
    assert msg.replies == ["режим обучения отключён"]


@pytest.mark.asyncio
async def test_exit_command_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(learning_handlers.settings, "learning_mode_enabled", False)
    msg = DummyMessage()
    update = cast(Update, SimpleNamespace(message=msg))
    context = SimpleNamespace(user_data={})
    await learning_handlers.exit_command(update, context)
    assert msg.replies == ["режим обучения отключён"]

