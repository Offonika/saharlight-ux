import os
from re import Pattern
from types import SimpleNamespace
from typing import Any, cast

from telegram import Update

import pytest
from telegram.ext import CallbackContext, ConversationHandler, MessageHandler

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
from services.api.app.diabetes.handlers import dose_handlers


def _filter_pattern_equals(h: Any, regex: str) -> bool:
    filt = getattr(h, "filters", None)
    pattern = getattr(filt, "pattern", None)
    return isinstance(pattern, Pattern) and pattern.pattern == regex


class DummyMessage:
    def __init__(self, text: str = "") -> None:
        self.text: str = text
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_sugar_back_fallback_cancels() -> None:
    handler = next(
        h
        for h in dose_handlers.sugar_conv.fallbacks
        if isinstance(h, MessageHandler) and _filter_pattern_equals(h, "^↩️ Назад$")
    )
    message = DummyMessage("↩️ Назад")
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"pending_entry": {"foo": "bar"}}),
    )
    result = await handler.callback(update, context)
    assert result == ConversationHandler.END
    assert message.replies and message.replies[-1] == "Отменено."
    assert context.user_data == {}


@pytest.mark.asyncio
async def test_cancel_command_clears_state() -> None:
    message = DummyMessage("/cancel")
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"pending_entry": {"foo": "bar"}}),
    )
    result = await dose_handlers.dose_cancel(update, context)
    assert result == ConversationHandler.END
    assert message.replies and message.replies[-1] == "Отменено."
    assert context.user_data == {}


def test_sugar_conv_has_back_fallback() -> None:
    fallbacks = dose_handlers.sugar_conv.fallbacks
    assert any(
        isinstance(h, MessageHandler)
        and h.callback is dose_handlers.dose_cancel
        and _filter_pattern_equals(h, "^↩️ Назад$")
        for h in fallbacks
    )