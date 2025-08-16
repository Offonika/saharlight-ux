from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext, ExtBot

import services.api.app.diabetes.handlers.security_handlers as handlers


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_hypoalert_faq_returns_message() -> None:
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[ExtBot[None], dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await handlers.hypo_alert_faq(update, context)

    assert message.replies, "Handler should reply with text"
    text = message.replies[0]
    assert "Гипогликемия" in text
    assert "Раннее предупреждение" in text