import os
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext, MessageHandler

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
from services.api.app.diabetes.handlers import dose_handlers


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
    handler = next(
        h
        for h in dose_handlers.dose_conv.fallbacks
        if isinstance(h, MessageHandler)
        and getattr(getattr(h, "filters", None), "pattern", None).pattern
        == "^📷 Фото еды$"
    )
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
