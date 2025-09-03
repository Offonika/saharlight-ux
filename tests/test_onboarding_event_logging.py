from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

import services.api.app.diabetes.handlers.onboarding_handlers as onboarding
import services.api.app.services.onboarding_state as onboarding_state


class DummyMessage:
    def __init__(self, text: str = "") -> None:
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text: str, **_: Any) -> None:
        self.replies.append(text)


class DummyQuery:
    def __init__(self, message: DummyMessage, data: str) -> None:
        self.message = message
        self.data = data

    async def answer(self) -> None:  # pragma: no cover - no logic
        pass


@pytest.fixture(autouse=True)
def fake_onboarding_state(monkeypatch: pytest.MonkeyPatch) -> None:
    async def save_state(
        user_id: int, step: int, data: dict[str, object], variant: str | None = None
    ) -> None:  # pragma: no cover - store not needed
        pass

    class DummyState:
        def __init__(self) -> None:
            self.step = onboarding.PROFILE
            self.data: dict[str, object] = {}
            self.variant = "var"
            self.completed_at = None

    async def load_state(user_id: int) -> DummyState:
        return DummyState()

    async def complete_state(user_id: int) -> None:  # pragma: no cover - no logic
        pass

    monkeypatch.setattr(onboarding_state, "save_state", save_state)
    monkeypatch.setattr(onboarding_state, "load_state", load_state)
    monkeypatch.setattr(onboarding_state, "complete_state", complete_state)


@pytest.mark.asyncio
async def test_profile_step_logs_event(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[tuple[int, str, int, str | None]] = []

    async def fake_log(user_id: int, name: str, step: int, variant: str | None) -> None:
        events.append((user_id, name, step, variant))

    monkeypatch.setattr(onboarding, "_log_event", fake_log, raising=False)

    message = DummyMessage()
    user = SimpleNamespace(id=1)
    update = cast(Update, SimpleNamespace(message=message, effective_user=user))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, job_queue=None, args=[]),
    )

    await onboarding.start_command(update, context)
    assert events[0] == (1, "onboarding_started", 0, "var")

    query = DummyQuery(message, f"{onboarding.CB_PROFILE_PREFIX}t2")
    update_cb = cast(
        Update, SimpleNamespace(callback_query=query, effective_user=user)
    )
    await onboarding.profile_chosen(update_cb, context)
    assert events[1] == (1, "step_completed_1", 1, "var")


@pytest.mark.asyncio
async def test_cancel_logs_event(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[tuple[int, str, int, str | None]] = []

    async def fake_log(user_id: int, name: str, step: int, variant: str | None) -> None:
        events.append((user_id, name, step, variant))

    monkeypatch.setattr(onboarding, "_log_event", fake_log, raising=False)

    message = DummyMessage()
    user = SimpleNamespace(id=2)
    update = cast(Update, SimpleNamespace(message=message, effective_user=user))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, job_queue=None, args=[]),
    )

    await onboarding.start_command(update, context)
    query = DummyQuery(message, onboarding.CB_CANCEL)
    update_cancel = cast(
        Update, SimpleNamespace(callback_query=query, effective_user=user)
    )
    state = await onboarding.profile_chosen(update_cancel, context)
    assert state == ConversationHandler.END
    assert events[1] == (2, "onboarding_canceled", 1, "var")
