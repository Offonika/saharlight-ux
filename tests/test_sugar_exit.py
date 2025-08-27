import os
from re import Pattern
from typing import Any

import pytest
from telegram.ext import ConversationHandler, MessageHandler
from tests.helpers import make_context, make_update
from tests.telegram_stubs import Message, User

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
from services.api.app.diabetes.handlers import dose_handlers


def _filter_pattern_equals(h: Any, regex: str) -> bool:
    filt = getattr(h, "filters", None)
    pattern = getattr(filt, "pattern", None)
    return isinstance(pattern, Pattern) and pattern.pattern == regex


@pytest.mark.asyncio
async def test_sugar_back_fallback_cancels() -> None:
    handler = next(
        h
        for h in dose_handlers.sugar_conv.fallbacks
        if isinstance(h, MessageHandler) and _filter_pattern_equals(h, "^↩️ Назад$")
    )
    message = Message(text="↩️ Назад")
    update = make_update(message=message, effective_user=User(id=1))
    context = make_context(user_data={"pending_entry": {"foo": "bar"}})
    result = await handler.callback(update, context)
    assert result == ConversationHandler.END
    assert message.texts and message.texts[-1] == "Отменено."
    assert context.user_data == {}


@pytest.mark.asyncio
async def test_cancel_command_clears_state() -> None:
    message = Message(text="/cancel")
    update = make_update(message=message, effective_user=User(id=1))
    context = make_context(user_data={"pending_entry": {"foo": "bar"}})
    result = await dose_handlers.dose_cancel(update, context)
    assert result == ConversationHandler.END
    assert message.texts and message.texts[-1] == "Отменено."
    assert context.user_data == {}


def test_sugar_conv_has_back_fallback():
    fallbacks = dose_handlers.sugar_conv.fallbacks
    assert any(
        isinstance(h, MessageHandler)
        and h.callback is dose_handlers.dose_cancel
        and _filter_pattern_equals(h, "^↩️ Назад$")
        for h in fallbacks
    )
