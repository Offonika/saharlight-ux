from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.diabetes import learning_onboarding


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)


@pytest.mark.asyncio
async def test_learn_reset_clears_user_data() -> None:
    user_data: dict[str, Any] = {
        "learn_profile_overrides": {"foo": "bar"},
        "learn_onboarding_stage": "stage",
    }
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(effective_message=message, message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data),
    )

    await learning_onboarding.learn_reset(update, context)

    assert user_data == {}
    assert message.replies == ["Учебный онбординг сброшен."]
