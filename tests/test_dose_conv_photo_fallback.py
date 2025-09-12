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
from services.api.app.diabetes.handlers import dose_calc
from services.api.app.diabetes.utils.ui import (
    PHOTO_BUTTON_PATTERN,
    PHOTO_BUTTON_TEXT,
)


def _find_handler(
    fallbacks: Iterable[
        BaseHandler[
            Update,
            CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        ]
    ],
    regex: str,
) -> MessageHandler[
    CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
    Any,
]:
    for h in fallbacks:
        if isinstance(h, MessageHandler):
            filt = getattr(h, "filters", None)
            pattern = getattr(filt, "pattern", None)
            if isinstance(pattern, Pattern) and pattern.pattern == regex:
                return h
    raise LookupError(regex)


class DummyMessage:
    def __init__(self, text: str = "") -> None:
        self.text: str = text
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_photo_button_cancels_and_prompts_photo() -> None:
    handler = _find_handler(dose_calc.dose_conv.fallbacks, PHOTO_BUTTON_PATTERN.pattern)
    message = DummyMessage(PHOTO_BUTTON_TEXT)
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"pending_entry": {"foo": "bar"}}),
    )
    await handler.callback(update, context)
    assert message.replies[0] == "Отменено."
    assert any("фото" in r.lower() for r in message.replies[1:])
    assert context.user_data == {}
