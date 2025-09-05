from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.diabetes.bot_start_handlers import build_start_handler


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_start_sends_webapp_links() -> None:
    handler = build_start_handler("https://ui.example")
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await handler.callback(update, context)

    assert message.replies == [
        "👋 Добро пожаловать! Быстрая настройка в приложении:"
    ]
    markup = message.kwargs[0]["reply_markup"]
    buttons = markup.inline_keyboard
    assert buttons[0][0].web_app.url == (
        "https://ui.example/profile?flow=onboarding&step=profile"
    )
    assert buttons[1][0].web_app.url == (
        "https://ui.example/reminders?flow=onboarding&step=reminders"
    )
