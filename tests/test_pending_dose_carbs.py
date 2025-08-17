from types import SimpleNamespace
from typing import Any, cast
import datetime

import pytest
from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.gpt_handlers as gpt_handlers

class DummyMessage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_freeform_pending_updates_dose_and_carbs() -> None:
    entry = {
        "telegram_id": 1,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
        "carbs_g": None,
        "xe": None,
        "dose": None,
        "sugar_before": None,
        "photo_path": None,
    }
    message = DummyMessage("dose=3.5 carbs=30")
    update = cast(Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"pending_entry": entry}),
    )

    await gpt_handlers.freeform_handler(update, context)

    assert entry["dose"] == 3.5
    assert entry["carbs_g"] == 30.0
    assert message.replies and "обновлены" in message.replies[0].lower()
