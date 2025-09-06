from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.diabetes.learning_onboarding import learn_reset


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)


@pytest.mark.asyncio
async def test_learn_reset_clears_user_data() -> None:
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message, effective_message=message))
    user_data = {
        "learn_profile_overrides": {"foo": "bar"},
        "learn_onboarding_stage": 1,
        "keep": 2,
    }
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data),
    )

    await learn_reset(update, context)

    assert user_data == {"keep": 2}
    assert message.replies == ["Учебный онбординг сброшен."]
