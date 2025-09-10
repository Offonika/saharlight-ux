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


class DummyMessage:
    def __init__(self) -> None:
        self.chat_id = 1

    async def reply_text(
        self, text: str
    ) -> None:  # pragma: no cover - fails intentionally
        raise telegram.error.TelegramError("fail")

    async def reply_video(self, video: Any, **_: Any) -> None:  # noqa: ANN401
        raise telegram.error.TelegramError("fail")


class DummyBot:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str) -> None:
        self.sent.append((chat_id, text))


class DummyTask:
    def cancel(self) -> None:  # pragma: no cover - test helper
        pass


def _fake_create_task(coro: Any) -> DummyTask:
    coro.close()
    return DummyTask()


@pytest.mark.asyncio
async def test_reset_onboarding_reply_error_fallback(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(asyncio, "create_task", _fake_create_task)
    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(
            effective_message=message, effective_user=SimpleNamespace(id=1)
        ),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=DummyBot(), user_data={}),
    )
    with caplog.at_level(logging.ERROR):
        await commands.reset_onboarding(update, context)
    assert context.bot.sent
    assert "Не удалось отправить предупреждение" in context.bot.sent[0][1]
    assert any(
        "Failed to send onboarding reset warning" in record.getMessage()
        for record in caplog.records
    )
