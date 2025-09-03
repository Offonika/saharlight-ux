from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

import services.api.app.diabetes.handlers.onboarding_handlers as onboarding
import services.api.app.services.onboarding_state as onboarding_state


@pytest.fixture(autouse=True)
def fake_onboarding_state(monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[int, dict[str, Any]] = {}
    steps: dict[int, int] = {}
    variants: dict[int, str | None] = {}

    async def save_state(
        user_id: int, step: int, data: dict[str, object], variant: str | None = None
    ) -> None:
        steps[user_id] = step
        store[user_id] = dict(data)
        variants[user_id] = variant

    class DummyState:
        def __init__(self, uid: int) -> None:
            self.user_id = uid
            self.step = steps[uid]
            self.data = store[uid]
            self.variant = variants[uid]
            self.completed_at = None

    async def load_state(user_id: int) -> DummyState | None:
        if user_id not in steps:
            return None
        return DummyState(user_id)

    async def complete_state(user_id: int) -> None:  # pragma: no cover - no logic
        pass

    monkeypatch.setattr(onboarding_state, "save_state", save_state)
    monkeypatch.setattr(onboarding_state, "load_state", load_state)
    monkeypatch.setattr(onboarding_state, "complete_state", complete_state)

    async def noop_mark(user_id: int) -> None:  # pragma: no cover - no logic
        pass

    monkeypatch.setattr(onboarding, "_mark_user_complete", noop_mark)

    async def noop_save_timezone(telegram_id: int, tz: str, *, auto: bool) -> bool:
        return True

    monkeypatch.setattr(onboarding, "save_timezone", noop_save_timezone)

    async def fake_create_reminder_from_preset(
        user_id: int, code: str, job_queue: Any
    ) -> Any:
        return SimpleNamespace(type=code, is_enabled=True)

    def fake_describe(rem: Any, user: Any | None = None) -> str:
        return f"R {getattr(rem, 'type', '')}"

    monkeypatch.setattr(
        onboarding.reminder_handlers,
        "create_reminder_from_preset",
        fake_create_reminder_from_preset,
    )
    monkeypatch.setattr(
        onboarding.reminder_handlers, "_describe", fake_describe, raising=False
    )


class DummyMessage:
    def __init__(self, text: str = "") -> None:
        self.text: str = text
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []
        self.web_app_data: Any | None = None

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
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, job_queue=None),
    )

    state = await onboarding.start_command(update, context)
    assert state == onboarding.PROFILE
    assert message.replies[-1].startswith("Шаг 1/3")

    query = DummyQuery(message, f"{onboarding.CB_PROFILE_PREFIX}t2")
    update_cb = cast(
        Update,
        SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1)),
    )
    state = await onboarding.profile_chosen(update_cb, context)
    assert state == onboarding.TIMEZONE
    assert message.replies[-1].startswith("Шаг 2/3")

    message.text = "Europe/Moscow"
    update_tz = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    state = await onboarding.timezone_text(update_tz, context)
    assert state == onboarding.REMINDERS
    assert message.replies[-1].startswith("Шаг 3/3")

    query_rem = DummyQuery(message, f"{onboarding.CB_REMINDER_PREFIX}sugar_08")
    update_rem = cast(
        Update,
        SimpleNamespace(callback_query=query_rem, effective_user=SimpleNamespace(id=1)),
    )
    state = await onboarding.reminders_chosen(update_rem, context)
    assert state == onboarding.REMINDERS

    query_done = DummyQuery(message, onboarding.CB_DONE)
    update_done = cast(
        Update,
        SimpleNamespace(
            callback_query=query_done, effective_user=SimpleNamespace(id=1)
        ),
    )
    state = await onboarding.reminders_chosen(update_done, context)
    assert state == ConversationHandler.END
    assert any("Готово" in r for r in message.replies)


@pytest.mark.asyncio
async def test_navigation_buttons() -> None:
    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, job_queue=None),
    )

    state = await onboarding.start_command(update, context)
    assert state == onboarding.PROFILE

    query_skip = DummyQuery(message, onboarding.CB_SKIP)
    update_skip = cast(
        Update,
        SimpleNamespace(
            callback_query=query_skip, effective_user=SimpleNamespace(id=1)
        ),
    )
    state = await onboarding.profile_chosen(update_skip, context)
    assert state == onboarding.TIMEZONE

    query_back = DummyQuery(message, onboarding.CB_BACK)
    update_back = cast(
        Update,
        SimpleNamespace(
            callback_query=query_back, effective_user=SimpleNamespace(id=1)
        ),
    )
    state = await onboarding.timezone_nav(update_back, context)
    assert state == onboarding.PROFILE

    query_cancel = DummyQuery(message, onboarding.CB_CANCEL)
    update_cancel = cast(
        Update,
        SimpleNamespace(
            callback_query=query_cancel, effective_user=SimpleNamespace(id=1)
        ),
    )
    state = await onboarding.profile_chosen(update_cancel, context)
    assert state == ConversationHandler.END


@pytest.mark.asyncio
async def test_resume_from_saved_step() -> None:
    user = SimpleNamespace(id=42)
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message, effective_user=user))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, args=[], job_queue=None),
    )
    await onboarding.start_command(update, context)
    query = DummyQuery(message, f"{onboarding.CB_PROFILE_PREFIX}t2")
    update_cb = cast(Update, SimpleNamespace(callback_query=query, effective_user=user))
    await onboarding.profile_chosen(update_cb, context)

    message2 = DummyMessage()
    update2 = cast(Update, SimpleNamespace(message=message2, effective_user=user))
    context2 = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, args=[], job_queue=None),
    )
    state = await onboarding.start_command(update2, context2)
    assert state == onboarding.TIMEZONE
    assert message2.replies[-1].startswith("Шаг 2/3")


@pytest.mark.asyncio
async def test_timezone_webapp_saves_and_moves_to_reminders() -> None:
    message = DummyMessage()
    message.web_app_data = SimpleNamespace(data="Europe/Moscow")
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    state = await onboarding.timezone_webapp(update, context)
    assert state == onboarding.REMINDERS
    assert context.user_data["timezone"] == "Europe/Moscow"
    assert message.replies[-1].startswith("Шаг 3/3")
