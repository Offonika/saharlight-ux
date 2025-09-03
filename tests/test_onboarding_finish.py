import pytest
from types import SimpleNamespace
from typing import Any, cast

from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

import services.api.app.diabetes.handlers.onboarding_handlers as onboarding
import services.api.app.services.onboarding_state as onboarding_state


class DummyMessage:
    def __init__(self, text: str = "") -> None:
        self.text = text
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
async def test_finish_creates_reminders(monkeypatch: pytest.MonkeyPatch) -> None:
    message = DummyMessage()
    user_data = {"reminders": {"sugar_08", "long_22"}}
    jq = object()

    async def complete_state(user_id: int) -> None:  # pragma: no cover - no logic
        pass

    async def mark_complete(user_id: int) -> None:  # pragma: no cover - no logic
        pass

    monkeypatch.setattr(onboarding_state, "complete_state", complete_state)
    monkeypatch.setattr(onboarding, "_mark_user_complete", mark_complete)
    monkeypatch.setattr(onboarding, "menu_keyboard", lambda: None)

    created: list[tuple[int, str, object]] = []

    async def create_reminder_from_preset(
        uid: int, code: str, jq_arg: object
    ) -> object:
        created.append((uid, code, jq_arg))
        return SimpleNamespace(kind=code)

    def describe(rem: Any, user: Any | None = None) -> str:
        return f"desc {rem.kind}"

    monkeypatch.setattr(
        onboarding.reminder_handlers,
        "create_reminder_from_preset",
        create_reminder_from_preset,
        raising=False,
    )
    monkeypatch.setattr(onboarding.reminder_handlers, "_describe", describe)

    await onboarding._finish(message, 1, user_data, jq)

    assert set(created) == {(1, "sugar_08", jq), (1, "long_22", jq)}
    assert any("Созданы напоминания" in r for r in message.replies)
    assert message.replies[-1].startswith("🎉 Готово!")


@pytest.mark.asyncio
async def test_reminders_chosen_passes_job_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage()
    query = DummyQuery(message, onboarding.CB_DONE)
    update = cast(
        Update,
        SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, job_queue="jq"),
    )

    async def load_state(user_id: int) -> None:  # pragma: no cover - no logic
        return None

    async def save_state(
        user_id: int, step: int, data: dict[str, Any], variant: str | None
    ) -> None:
        pass

    monkeypatch.setattr(onboarding_state, "load_state", load_state)
    monkeypatch.setattr(onboarding_state, "save_state", save_state)

    called: dict[str, Any] = {}

    async def fake_finish(
        msg: DummyMessage,
        uid: int,
        data: dict[str, Any],
        jq_arg: object,
    ) -> int:
        called["user_data"] = data
        called["job_queue"] = jq_arg
        return ConversationHandler.END

    monkeypatch.setattr(onboarding, "_finish", fake_finish)

    state = await onboarding.reminders_chosen(update, context)

    assert state == ConversationHandler.END
    assert called["user_data"] is context.user_data
    assert called["job_queue"] == context.job_queue
