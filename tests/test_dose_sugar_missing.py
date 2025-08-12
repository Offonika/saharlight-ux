import datetime
import os
from types import SimpleNamespace
from typing import Any

import pytest
from telegram.ext import ConversationHandler

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
