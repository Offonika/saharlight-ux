from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.diabetes.onboarding_state import (
    OnboardingStateStore,
    reset_onboarding,
)
from tests.utils.warn_ctx import warn_or_not


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)


@pytest.mark.asyncio
async def test_reset_command() -> None:
    store = OnboardingStateStore()
    store.set_step(1, 2)
    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(
            message=message,
            effective_user=SimpleNamespace(id=1),
            effective_message=message,
        ),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(application=SimpleNamespace(bot_data={"onb_state": store})),
    )
    with warn_or_not(None):
        await reset_onboarding(update, context)
    assert store.get(1).step == 0
    assert message.replies and "reset" in message.replies[-1].lower()


def test_continue_after_restart() -> None:
    store = OnboardingStateStore()
    store.set_step(1, 2)
    data = store.to_dict()
    with warn_or_not(None):
        restored = OnboardingStateStore.from_dict(data)
    assert restored.get(1).step == 2


def test_auto_reset_after_inactivity() -> None:
    store = OnboardingStateStore()
    state = store.get(1)
    state.step = 2
    state.updated_at = datetime.now(UTC) - timedelta(days=15)
    with warn_or_not(None):
        new_state = store.get(1)
    assert new_state.step == 0
