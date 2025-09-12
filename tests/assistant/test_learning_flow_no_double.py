from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from services.api.app.config import settings
from services.api.app.diabetes import learning_handlers
from services.api.app.diabetes.learning_state import LearnState, get_state, set_state


class DummyMessage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.from_user = SimpleNamespace(id=1)
        self.sent: list[str] = []

    async def reply_text(self, text: str, **_: Any) -> None:  # pragma: no cover - helper
        self.sent.append(text)


@pytest.mark.asyncio
async def test_learning_flow_no_double(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(settings, "learning_mode_enabled", True)
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")
    monkeypatch.setattr(settings, "learning_logging_required", False)

    async def fake_check_user_answer(*_: object, **__: object) -> tuple[bool, str]:
        calls.append("check_user_answer")
        return True, "feedback"

    async def fake_next_step(*_: object, **__: object) -> str:
        calls.append("next_step")
        return "next question"

    async def fake_safe_add_lesson_log(*_: object, **__: object) -> bool:
        return False

    monkeypatch.setattr(learning_handlers, "check_user_answer", fake_check_user_answer)
    monkeypatch.setattr(learning_handlers, "generate_step_text", fake_next_step)
    monkeypatch.setattr(learning_handlers, "safe_add_lesson_log", fake_safe_add_lesson_log)
    async def ok_hydrate(*_a: object, **_k: object) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "_hydrate", ok_hydrate)
    monkeypatch.setattr(learning_handlers, "_rate_limited", lambda *_a, **_k: False)
    monkeypatch.setattr(learning_handlers, "build_main_keyboard", lambda: None)
    monkeypatch.setattr(learning_handlers, "sanitize_feedback", lambda s: s)
    monkeypatch.setattr(learning_handlers, "format_reply", lambda s: s)
    monkeypatch.setattr(learning_handlers, "ensure_single_question", lambda s: s)

    user_data: dict[str, object] = {}
    set_state(user_data, LearnState(topic="t", step=0, awaiting=True, last_step_text="q"))

    msg = DummyMessage("ans")

    async def track_send(text: str, **_: Any) -> None:
        calls.append("sendMessage")
        await DummyMessage.reply_text(msg, text)

    msg.reply_text = track_send  # type: ignore[method-assign]

    update = SimpleNamespace(message=msg, effective_user=msg.from_user)
    context = SimpleNamespace(user_data=user_data, bot_data={})

    await learning_handlers.lesson_answer_handler(update, context)

    assert calls == ["check_user_answer", "next_step", "sendMessage"]
    assert msg.sent == ["feedback\n\n—\n\nnext question"]
    state = get_state(user_data)
    assert state is not None
    assert state.step == 1
