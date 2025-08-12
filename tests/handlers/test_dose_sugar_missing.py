import datetime
from types import SimpleNamespace
import os

import pytest
from telegram.ext import ConversationHandler

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
import diabetes.utils.openai_utils as openai_utils  # noqa: F401
from diabetes.handlers import dose_handlers


class DummyMessage:
    def __init__(self, text=""):
        self.text = text
        self.replies: list[str] = []
        self.kwargs: list[dict] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_dose_sugar_requires_carbs_or_xe():
    entry = {
        "telegram_id": 1,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
    }
    message = DummyMessage("5.5")
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data={"pending_entry": entry})

    result = await dose_handlers.dose_sugar(update, context)

    assert result == ConversationHandler.END
    assert message.replies and "углев" in message.replies[0].lower()
    assert context.user_data == {}
