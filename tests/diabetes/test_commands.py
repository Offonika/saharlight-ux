from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.diabetes import commands
from services.api.app.diabetes.onboarding_state import OnboardingStateStore


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)


class DummyApp:
    def __init__(self) -> None:
        self.bot_data: dict[str, object] = {}


@pytest.mark.asyncio
async def test_help_mentions_webapp() -> None:
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await commands.help_command(update, context)

    text = message.replies[0]
    assert "/start" in text
    assert "WebApp" in text


@pytest.mark.asyncio
async def test_reset_onboarding_warns_and_resets() -> None:
    message = DummyMessage()
    user = SimpleNamespace(id=1)
    update = cast(
        Update,
        SimpleNamespace(effective_message=message, message=message, effective_user=user),
    )
    app = DummyApp()
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(application=app, user_data={}),
    )
    store = OnboardingStateStore()
    store.set_step(1, 2)
    app.bot_data["onb_state"] = store

    await commands.reset_onboarding(update, context)
    assert "подтверж" in message.replies[0].lower()
    assert store.get(1).step == 2

    message.replies.clear()
    await commands.reset_onboarding(update, context)
    assert store.get(1).step == 0
    assert "сброшен" in message.replies[0].lower()
