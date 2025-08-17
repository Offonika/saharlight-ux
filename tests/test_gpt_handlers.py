from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.gpt_handlers as gpt_handlers


class DummyMessage:
    def __init__(self) -> None:
        self.texts: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)


@pytest.mark.asyncio
async def test_chat_with_gpt_replies() -> None:
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]], SimpleNamespace())
    await gpt_handlers.chat_with_gpt(update, context)
    assert message.texts == ["🗨️ Чат с GPT временно недоступен."]
