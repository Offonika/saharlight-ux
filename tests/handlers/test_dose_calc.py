import datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.diabetes.handlers import dose_calc
from services.api.app.diabetes.utils.ui import LONG_INSULIN_BUTTON_TEXT
from services.api.app.diabetes.utils.constants import MAX_SUGAR_MMOL_L


class DummyMessage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)


@pytest.mark.asyncio
async def test_dose_sugar_rejects_high_value() -> None:
    message = DummyMessage(str(MAX_SUGAR_MMOL_L + 1))
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"pending_entry": {"carbs_g": 10}}, chat_data={}),
    )

    result = await dose_calc.dose_sugar(update, context)

    assert result == dose_calc.DoseState.SUGAR
    assert any(
        "не должен превышать" in text and str(MAX_SUGAR_MMOL_L) in text
        for text in message.replies
    )


@pytest.mark.asyncio
async def test_dose_type_choice_switches_to_long() -> None:
    message = DummyMessage(LONG_INSULIN_BUTTON_TEXT)
    user_data: dict[str, Any] = {}
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=7)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data, chat_data={}),
    )

    result = await dose_calc.dose_type_choice(update, context)

    assert result == dose_calc.DoseState.LONG
    assert any("длинного" in reply for reply in message.replies)
    pending = user_data.get("pending_entry")
    assert isinstance(pending, dict)
    assert pending["telegram_id"] == 7


@pytest.mark.asyncio
async def test_dose_long_rounds_and_confirms() -> None:
    now = datetime.datetime.now(datetime.timezone.utc)
    message = DummyMessage("7.26")
    user_data: dict[str, Any] = {
        "pending_entry": {"telegram_id": 5, "event_time": now},
    }
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=5)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data, chat_data={}),
    )

    result = await dose_calc.dose_long(update, context)

    assert result == dose_calc.END
    pending = user_data["pending_entry"]
    assert pending["insulin_long"] == 7.5
    assert any("7.5" in reply for reply in message.replies)


@pytest.mark.asyncio
async def test_dose_long_rejects_too_high_value() -> None:
    message = DummyMessage("250")
    user_data: dict[str, Any] = {"pending_entry": {}}
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=9)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data, chat_data={}),
    )

    result = await dose_calc.dose_long(update, context)

    assert result == dose_calc.DoseState.LONG
    assert any("не должна превышать" in reply for reply in message.replies)

