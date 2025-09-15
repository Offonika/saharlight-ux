from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import asyncio
import logging

import pytest
import telegram
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.diabetes import commands
from services.api.app.diabetes.onboarding_state import OnboardingStateStore
from tests.utils.warn_ctx import warn_or_not


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)


class DummyApp:
    def __init__(self) -> None:
        self.bot_data: dict[str, object] = {}


@pytest.mark.asyncio
async def test_help_mentions_webapp() -> None:
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await commands.help_command(update, context)

    text = message.replies[0]
    assert "/start" in text
    assert "WebApp" in text
    assert "/topics" in text


@pytest.mark.asyncio
async def test_reset_onboarding_warns_and_resets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage()
    user = SimpleNamespace(id=1)
    update = cast(
        Update,
        SimpleNamespace(
            effective_message=message, message=message, effective_user=user
        ),
    )
    app = DummyApp()
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(application=app, user_data={}),
    )
    store = OnboardingStateStore()
    store.set_step(1, 2)
    app.bot_data["onb_state"] = store

    async def dummy_reset(update: Update, context: CallbackContext) -> int:
        store.reset(user.id)
        await message.reply_text(
            "Онбординг сброшен. Отправьте /start, чтобы начать заново."
        )
        return 0

    monkeypatch.setattr(commands, "_reset_onboarding", dummy_reset)

    await commands.reset_onboarding(update, context)
    assert "подтверж" in message.replies[0].lower()
    assert store.get(1).step == 2

    message.replies.clear()
    await commands.reset_onboarding(update, context)
    assert store.get(1).step == 0
    assert "сброшен" in message.replies[0].lower()


@pytest.mark.asyncio
async def test_reset_onboarding_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    message = DummyMessage()
    user = SimpleNamespace(id=1)
    update = cast(
        Update,
        SimpleNamespace(
            effective_message=message, message=message, effective_user=user
        ),
    )
    app = DummyApp()
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(application=app, user_data={}),
    )

    async def fast_sleep(_: float) -> None:
        return

    monkeypatch.setattr(commands.asyncio, "sleep", fast_sleep)

    await commands.reset_onboarding(update, context)
    task = context.user_data.get("_onb_reset_task")
    assert isinstance(task, asyncio.Task)
    await task

    assert "_onb_reset_confirm" not in context.user_data
    assert "_onb_reset_task" not in context.user_data
    assert any("не подтвержд" in r.lower() for r in message.replies)


@pytest.mark.asyncio
async def test_reset_onboarding_timeout_telegram_error(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    class FailingMessage:
        def __init__(self) -> None:
            self.replies: list[str] = []
            self.calls = 0

        async def reply_text(self, text: str) -> None:
            self.calls += 1
            if self.calls > 1:
                raise telegram.error.TelegramError("fail")
            self.replies.append(text)

    message = FailingMessage()
    user = SimpleNamespace(id=1)
    update = cast(
        Update,
        SimpleNamespace(
            effective_message=message, message=message, effective_user=user
        ),
    )
    app = DummyApp()
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(application=app, user_data={}),
    )

    async def fast_sleep(_: float) -> None:
        return

    monkeypatch.setattr(commands.asyncio, "sleep", fast_sleep)

    with caplog.at_level(logging.ERROR):
        await commands.reset_onboarding(update, context)
        task = context.user_data.get("_onb_reset_task")
        assert isinstance(task, asyncio.Task)
        await task
        assert any(
            "Failed to notify about onboarding reset timeout" in r.message
            for r in caplog.records
        )

    assert task.exception() is None
    assert len(message.replies) == 1
    assert "_onb_reset_confirm" not in context.user_data
    assert "_onb_reset_task" not in context.user_data


@pytest.mark.asyncio
async def test_reset_onboarding_timeout_unexpected_error(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    class FailingMessage:
        def __init__(self) -> None:
            self.replies: list[str] = []
            self.calls = 0

        async def reply_text(self, text: str) -> None:
            self.calls += 1
            if self.calls > 1:
                raise ValueError("boom")
            self.replies.append(text)

    message = FailingMessage()
    user = SimpleNamespace(id=1)
    update = cast(
        Update,
        SimpleNamespace(
            effective_message=message, message=message, effective_user=user
        ),
    )
    app = DummyApp()
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(application=app, user_data={}),
    )

    async def fast_sleep(_: float) -> None:
        return

    monkeypatch.setattr(commands.asyncio, "sleep", fast_sleep)

    with caplog.at_level(logging.ERROR):
        await commands.reset_onboarding(update, context)
        task = context.user_data.get("_onb_reset_task")
        assert isinstance(task, asyncio.Task)
        with pytest.raises(ValueError):
            await task
        assert any(
            "Reset onboarding timeout task failed" in r.message for r in caplog.records
        )

    assert task.exception() is not None
    assert isinstance(task.exception(), ValueError)
    assert len(message.replies) == 1
    assert "_onb_reset_confirm" not in context.user_data
    assert "_onb_reset_task" not in context.user_data


@pytest.mark.asyncio
async def test_reset_onboarding_consume_cancelled_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure timeout task is awaited when onboarding reset is confirmed."""

    message = DummyMessage()
    user = SimpleNamespace(id=1)
    update = cast(
        Update,
        SimpleNamespace(
            effective_message=message, message=message, effective_user=user
        ),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"_onb_reset_confirm": True}),
    )

    async def dummy_reset(
        update: Update, context: CallbackContext
    ) -> int:  # noqa: ARG001
        return 0

    monkeypatch.setattr(commands, "_reset_onboarding", dummy_reset)

    class DummyTask(asyncio.Task):
        def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
            async def sleeper() -> None:
                await asyncio.sleep(3600)

            super().__init__(sleeper(), loop=loop)
            self.cancel_called = False
            self.awaited = False

        def cancel(self) -> bool:  # type: ignore[override]
            self.cancel_called = True
            return super().cancel()

        def __await__(self):  # type: ignore[override]
            self.awaited = True
            return super().__await__()

    task = DummyTask(asyncio.get_running_loop())
    context.user_data["_onb_reset_task"] = task

    with warn_or_not(None):
        await commands.reset_onboarding(update, context)

    assert task.cancel_called
    assert task.awaited
