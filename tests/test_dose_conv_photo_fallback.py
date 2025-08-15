from __future__ import annotations

import os
from re import Pattern
from types import SimpleNamespace
from typing import Any, Iterable, cast

import pytest
from telegram import Update
from telegram.ext import BaseHandler, CallbackContext, MessageHandler

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
from services.api.app.diabetes.handlers import dose_handlers


def _find_handler(
    fallbacks: Iterable[BaseHandler[Any, Any]],
    regex: str,
) -> MessageHandler[Any, Any]:
    for h in fallbacks:
        if isinstance(h, MessageHandler):
            filt = getattr(h, "filters", None)
            pattern = getattr(filt, "pattern", None)
            if isinstance(pattern, Pattern) and pattern.pattern == regex:
                return h
    raise LookupError(regex)


class DummyMessage:
    def __init__(self, text: str = ""):
        self.text = text
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_photo_button_cancels_and_prompts_photo() -> None:
    handler = _find_handler(dose_handlers.dose_conv.fallbacks, "^📷 Фото еды$")
    message = DummyMessage("📷 Фото еды")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, Any, Any, Any],
        SimpleNamespace(user_data={"pending_entry": {"foo": "bar"}}),
    )
    await handler.callback(update, context)
    assert message.replies[0] == "Отменено."
    assert any("фото" in r.lower() for r in message.replies[1:])
    assert context.user_data == {}
