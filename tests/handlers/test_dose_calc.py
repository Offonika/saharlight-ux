from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.diabetes.handlers import dose_calc
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

