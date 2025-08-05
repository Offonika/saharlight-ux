from types import SimpleNamespace
import os

import pytest
from telegram.ext import MessageHandler

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
import diabetes.openai_utils as openai_utils  # noqa: F401
from diabetes import (
    dose_handlers,
    reminder_handlers,
    profile_handlers,
    onboarding_handlers,
    sos_handlers,
)


class DummyMessage:
    def __init__(self, text: str = ""):
        self.text = text
        self.replies: list[str] = []
        self.kwargs: list[dict] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)
        self.kwargs.append(kwargs)


async def _exercise(handler):
    message = DummyMessage("📷 Фото еды")
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data={"pending_entry": {"foo": "bar"}, "dose_method": "xe"})
    await handler.callback(update, context)
    assert message.replies[0] == "Отменено."
    assert any("фото" in r.lower() for r in message.replies[1:])
    assert context.user_data == {}


@pytest.mark.asyncio
async def test_add_reminder_conv_photo_fallback():
    handler = next(
        h
        for h in reminder_handlers.add_reminder_conv.fallbacks
        if isinstance(h, MessageHandler)
        and getattr(getattr(h, "filters", None), "pattern", None).pattern
        == "^📷 Фото еды$"
    )
    await _exercise(handler)


@pytest.mark.asyncio
async def test_profile_conv_photo_fallback():
    handler = next(
        h
        for h in profile_handlers.profile_conv.fallbacks
        if isinstance(h, MessageHandler)
        and getattr(getattr(h, "filters", None), "pattern", None).pattern
        == "^📷 Фото еды$"
    )
    await _exercise(handler)


@pytest.mark.asyncio
async def test_sugar_conv_photo_fallback():
    handler = next(
        h
        for h in dose_handlers.sugar_conv.fallbacks
        if isinstance(h, MessageHandler)
        and getattr(getattr(h, "filters", None), "pattern", None).pattern
        == "^📷 Фото еды$"
    )
    await _exercise(handler)


@pytest.mark.asyncio
async def test_onboarding_conv_photo_fallback():
    handler = next(
        h
        for h in onboarding_handlers.onboarding_conv.fallbacks
        if isinstance(h, MessageHandler)
        and getattr(getattr(h, "filters", None), "pattern", None).pattern
        == "^📷 Фото еды$"
    )
    await _exercise(handler)


@pytest.mark.asyncio
async def test_sos_contact_conv_photo_fallback():
    handler = next(
        h
        for h in sos_handlers.sos_contact_conv.fallbacks
        if isinstance(h, MessageHandler)
        and getattr(getattr(h, "filters", None), "pattern", None).pattern
        == "^📷 Фото еды$"
    )
    await _exercise(handler)
