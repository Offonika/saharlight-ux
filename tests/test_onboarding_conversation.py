from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

import services.api.app.diabetes.handlers.onboarding_handlers as onboarding


class DummyMessage:
    def __init__(self, text: str = "") -> None:
        self.text: str = text
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


class DummyQuery:
    def __init__(self, message: DummyMessage, data: str) -> None:
        self.message = message
        self.data = data

    async def answer(self) -> None:  # pragma: no cover - no logic
        pass


@pytest.mark.asyncio
async def test_happy_path() -> None:
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)))
    context = cast(CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]], SimpleNamespace(user_data={}))

    state = await onboarding.start_command(update, context)
    assert state == onboarding.PROFILE
    assert message.replies[-1].startswith("Шаг 1/3")

    query = DummyQuery(message, f"{onboarding.CB_PROFILE_PREFIX}t2")
    update_cb = cast(Update, SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1)))
    state = await onboarding.profile_chosen(update_cb, context)
    assert state == onboarding.TIMEZONE
    assert message.replies[-1].startswith("Шаг 2/3")

    message.text = "Europe/Moscow"
    update_tz = cast(Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)))
    state = await onboarding.timezone_text(update_tz, context)
    assert state == onboarding.REMINDERS
    assert message.replies[-1].startswith("Шаг 3/3")

    query_rem = DummyQuery(message, f"{onboarding.CB_REMINDER_PREFIX}sugar_08")
    update_rem = cast(Update, SimpleNamespace(callback_query=query_rem, effective_user=SimpleNamespace(id=1)))
    state = await onboarding.reminders_chosen(update_rem, context)
    assert state == onboarding.REMINDERS

    query_done = DummyQuery(message, onboarding.CB_DONE)
    update_done = cast(Update, SimpleNamespace(callback_query=query_done, effective_user=SimpleNamespace(id=1)))
    state = await onboarding.reminders_chosen(update_done, context)
    assert state == ConversationHandler.END
    assert any("Готово" in r for r in message.replies)


@pytest.mark.asyncio
async def test_navigation_buttons() -> None:
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)))
    context = cast(CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]], SimpleNamespace(user_data={}))

    state = await onboarding.start_command(update, context)
    assert state == onboarding.PROFILE

    query_skip = DummyQuery(message, onboarding.CB_SKIP)
    update_skip = cast(Update, SimpleNamespace(callback_query=query_skip, effective_user=SimpleNamespace(id=1)))
    state = await onboarding.profile_chosen(update_skip, context)
    assert state == onboarding.TIMEZONE

    query_back = DummyQuery(message, onboarding.CB_BACK)
    update_back = cast(Update, SimpleNamespace(callback_query=query_back, effective_user=SimpleNamespace(id=1)))
    state = await onboarding.timezone_nav(update_back, context)
    assert state == onboarding.PROFILE

    query_cancel = DummyQuery(message, onboarding.CB_CANCEL)
    update_cancel = cast(Update, SimpleNamespace(callback_query=query_cancel, effective_user=SimpleNamespace(id=1)))
    state = await onboarding.profile_chosen(update_cancel, context)
    assert state == ConversationHandler.END

    state = await onboarding.start_command(update, context)
    assert state == onboarding.PROFILE

    query_prof = DummyQuery(message, f"{onboarding.CB_PROFILE_PREFIX}t1")
    update_prof = cast(Update, SimpleNamespace(callback_query=query_prof, effective_user=SimpleNamespace(id=1)))
    state = await onboarding.profile_chosen(update_prof, context)
    assert state == onboarding.TIMEZONE

    query_skip2 = DummyQuery(message, onboarding.CB_SKIP)
    update_skip2 = cast(Update, SimpleNamespace(callback_query=query_skip2, effective_user=SimpleNamespace(id=1)))
    state = await onboarding.timezone_nav(update_skip2, context)
    assert state == onboarding.REMINDERS

    query_back3 = DummyQuery(message, onboarding.CB_BACK)
    update_back3 = cast(Update, SimpleNamespace(callback_query=query_back3, effective_user=SimpleNamespace(id=1)))
    state = await onboarding.reminders_chosen(update_back3, context)
    assert state == onboarding.TIMEZONE

    query_skip3 = DummyQuery(message, onboarding.CB_SKIP)
    update_skip3 = cast(Update, SimpleNamespace(callback_query=query_skip3, effective_user=SimpleNamespace(id=1)))
    state = await onboarding.reminders_chosen(update_skip3, context)
    assert state == ConversationHandler.END
