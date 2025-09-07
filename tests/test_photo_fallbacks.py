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
from services.api.app.diabetes.handlers import (
    dose_calc,
    profile as profile_handlers,
    onboarding_handlers,
    sos_handlers,
)
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


async def _exercise(
    handler: MessageHandler[
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        Any,
    ],
) -> None:
    message = DummyMessage(PHOTO_BUTTON_TEXT)
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            user_data={"pending_entry": {"foo": "bar"}, "dose_method": "xe"}
        ),
    )
    await handler.callback(update, context)
    assert message.replies[0] == "Отменено."
    assert any("фото" in r.lower() for r in message.replies[1:])
    assert context.user_data == {}


@pytest.mark.asyncio
async def test_profile_conv_photo_fallback() -> None:
    handler = _find_handler(
        profile_handlers.profile_conv.fallbacks, PHOTO_BUTTON_PATTERN.pattern
    )
    await _exercise(handler)


@pytest.mark.asyncio
async def test_sugar_conv_photo_fallback() -> None:
    handler = _find_handler(dose_calc.sugar_conv.fallbacks, PHOTO_BUTTON_PATTERN.pattern)
    await _exercise(handler)


@pytest.mark.asyncio
async def test_onboarding_conv_photo_fallback() -> None:
    handler = _find_handler(
        onboarding_handlers.onboarding_conv.fallbacks, PHOTO_BUTTON_PATTERN.pattern
    )
    await _exercise(handler)


@pytest.mark.asyncio
async def test_sos_contact_conv_photo_fallback() -> None:
    handler = _find_handler(
        sos_handlers.sos_contact_conv.fallbacks, PHOTO_BUTTON_PATTERN.pattern
    )
    await _exercise(handler)
