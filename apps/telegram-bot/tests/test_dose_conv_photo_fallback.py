from types import SimpleNamespace
import os

import pytest
from telegram.ext import MessageHandler

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
import diabetes.openai_utils as openai_utils  # noqa: F401
from diabetes import dose_handlers


class DummyMessage:
    def __init__(self, text=""):
        self.text = text
        self.replies: list[str] = []
        self.kwargs: list[dict] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_photo_button_cancels_and_prompts_photo():
    handler = next(
        h
        for h in dose_handlers.dose_conv.fallbacks
        if isinstance(h, MessageHandler)
        and getattr(getattr(h, "filters", None), "pattern", None).pattern
        == "^📷 Фото еды$"
    )
    message = DummyMessage("📷 Фото еды")
    update = SimpleNamespace(
        message=message, effective_user=SimpleNamespace(id=1)
    )
    context = SimpleNamespace(user_data={"pending_entry": {"foo": "bar"}})
    await handler.callback(update, context)
    assert message.replies[0] == "Отменено."
    assert any("фото" in r.lower() for r in message.replies[1:])
    assert context.user_data == {}
