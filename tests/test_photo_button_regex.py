import os
import re
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

import services.api.app.diabetes.handlers.photo_handlers as photo_handlers
import services.api.app.diabetes.handlers.registration as handlers


class DummyMessage:
    def __init__(self, text: str) -> None:
        self.text: str = text
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_photo_button_without_emoji_triggers_prompt() -> None:
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")

    app = ApplicationBuilder().token("TESTTOKEN").build()
    handlers.register_handlers(app)
    photo_handler = next(
        h
        for h in app.handlers[0]
        if isinstance(h, MessageHandler) and h.callback is photo_handlers.photo_prompt
    )
    pattern = cast(filters.Regex, photo_handler.filters).pattern.pattern
    assert re.fullmatch(pattern, "Фото еды")

    message = DummyMessage("Фото еды")
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(ContextTypes.DEFAULT_TYPE, SimpleNamespace())
    result = await photo_handler.callback(update, context)
    assert result is None
    assert message.replies == ["📸 Пришлите фото блюда для анализа."]
