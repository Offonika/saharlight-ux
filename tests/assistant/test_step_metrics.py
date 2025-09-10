from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from services.api.app.config import settings
from services.api.app.diabetes import learning_handlers
from services.api.app.diabetes.learning_state import LearnState, set_state
from services.api.app.diabetes.metrics import step_advance_total


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.from_user = SimpleNamespace(id=1)
        self.replies: list[str] = []

    async def reply_text(self, text: str, **_: Any) -> None:  # pragma: no cover - helper
        self.replies.append(text)


@pytest.mark.asyncio
async def test_step_advance_counter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")
    async def _ok_hydrate(*_a: object, **_k: object) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "_hydrate", _ok_hydrate)
    monkeypatch.setattr(learning_handlers, "_rate_limited", lambda *_a, **_k: False)
    monkeypatch.setattr(learning_handlers, "build_main_keyboard", lambda: None)

    async def fake_check_user_answer(*_a: object, **_k: object) -> tuple[bool, str]:
        return True, "fb"

    async def fake_generate_step_text(*_a: object, **_k: object) -> str:
        return "next"

    async def fake_safe_add_lesson_log(*_a: object, **_k: object) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "check_user_answer", fake_check_user_answer)
    monkeypatch.setattr(learning_handlers, "generate_step_text", fake_generate_step_text)
    monkeypatch.setattr(learning_handlers, "safe_add_lesson_log", fake_safe_add_lesson_log)

    step_advance_total._value.set(0)  # type: ignore[attr-defined] # noqa: SLF001

    user_data: dict[str, object] = {}
    set_state(user_data, LearnState(topic="t", step=1, awaiting=True, last_step_text="q"))

    msg = DummyMessage("ans")
    update = SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data=user_data, bot_data={})

    await learning_handlers.lesson_answer_handler(update, context)

    assert step_advance_total._value.get() == 1  # type: ignore[attr-defined]
