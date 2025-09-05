from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.bot_start_handlers as start_handlers
from services.api.app.diabetes.bot_start_handlers import build_start_handler


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


async def _invoke_handler(variant: str) -> tuple[DummyMessage, list[list[Any]]]:
    handler = build_start_handler("https://ui.example")
    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    start_handlers.choose_variant = lambda _uid: variant  # type: ignore[assignment]

    await handler.callback(update, context)
    markup = message.kwargs[0]["reply_markup"]
    return message, markup.inline_keyboard


@pytest.mark.asyncio
async def test_start_variant_a() -> None:
    message, buttons = await _invoke_handler("A")

    assert message.replies == ["👋 Добро пожаловать! Быстрая настройка в приложении:"]
    assert buttons[0][0].web_app.url == (
        "https://ui.example/profile?flow=onboarding&step=profile&variant=A"
    )
    assert buttons[1][0].web_app.url == (
        "https://ui.example/reminders?flow=onboarding&step=reminders&variant=A"
    )


@pytest.mark.asyncio
async def test_start_variant_b() -> None:
    message, buttons = await _invoke_handler("B")

    assert message.replies == ["👋 Добро пожаловать! Быстрая настройка в приложении:"]
    assert buttons[0][0].web_app.url == (
        "https://ui.example/reminders?flow=onboarding&step=reminders&variant=B"
    )
    assert buttons[1][0].web_app.url == (
        "https://ui.example/profile?flow=onboarding&step=profile&variant=B"
    )
