import datetime
import os
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
from services.api.app.diabetes.handlers import dose_calc


class DummyMessage:
    def __init__(self, text: str = "") -> None:
        self.text: str = text
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_dose_sugar_requires_carbs_or_xe() -> None:
    entry = {
        "telegram_id": 1,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
    }
    message = DummyMessage("5.5")
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"pending_entry": entry}),
    )

    result = await dose_calc.dose_sugar(update, context)

    assert result == dose_calc.DoseState.METHOD
    assert message.replies and "углев" in message.replies[0].lower()
    assert context.user_data == {}



@pytest.mark.asyncio
async def test_dose_sugar_requires_pending_entry() -> None:
    message = DummyMessage("5.5")
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )

    result = await dose_calc.dose_sugar(update, context)

    assert result == dose_calc.DoseState.METHOD
    assert message.replies and "углев" in message.replies[0].lower()
    assert context.user_data == {}
