from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Mapping

import pytest

from services.api.app.config import settings
from services.api.app.diabetes import learning_handlers
from services.api.app.diabetes.learning_state import get_state
from services.api.app.diabetes.services import lesson_log


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.from_user = SimpleNamespace(id=1)
        self.replies: list[str] = []

    async def reply_text(self, text: str, **_: Any) -> None:
        self.replies.append(text)


@pytest.mark.asyncio
async def test_flow_idk_with_log_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate start→next→answer('Не знаю')→next flow with log failures."""

    monkeypatch.setattr(settings, "learning_mode_enabled", True)
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")
    monkeypatch.setattr(settings, "learning_logging_required", False)

    async def fake_ensure_overrides(*_: object) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "ensure_overrides", fake_ensure_overrides)
    monkeypatch.setattr(learning_handlers, "build_main_keyboard", lambda: None)
    monkeypatch.setattr(
        learning_handlers,
        "generate_learning_plan",
        lambda _: ["step1?", "step2?", "step3?", "step4?"],
    )
    monkeypatch.setattr(learning_handlers, "format_reply", lambda t: t)
    monkeypatch.setattr(learning_handlers, "TOPICS_RU", {"slug": "Topic"})
    monkeypatch.setattr(learning_handlers, "_rate_limited", lambda *a, **k: False)

    async def fake_start_lesson(user_id: int, slug: str) -> SimpleNamespace:
        return SimpleNamespace(lesson_id=1)

    steps_iter = iter(["step1?", "step2?", "step3?", "step4?"])

    async def fake_next_step(
        user_id: int,
        lesson_id: int,
        profile: Mapping[str, str | None],
        prev_summary: str | None = None,
    ) -> tuple[str, bool]:
        return next(steps_iter), False

    monkeypatch.setattr(learning_handlers.curriculum_engine, "start_lesson", fake_start_lesson)
    monkeypatch.setattr(learning_handlers.curriculum_engine, "next_step", fake_next_step)

    async def fake_check_user_answer(
        profile: Mapping[str, str | None],
        topic: str,
        answer: str,
        last: str,
    ) -> tuple[bool, str]:
        return True, "fb"

    monkeypatch.setattr(learning_handlers, "check_user_answer", fake_check_user_answer)

    async def fake_assistant_chat(*_: object) -> str:
        return "fb"

    monkeypatch.setattr(learning_handlers, "assistant_chat", fake_assistant_chat)

    async def fail_run_db(*_: object, **__: object) -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(lesson_log, "run_db", fail_run_db)
    lesson_log.pending_logs.clear()

    context = SimpleNamespace(user_data={}, bot_data={}, args=["slug"])

    msg_start = DummyMessage()
    update_start = SimpleNamespace(message=msg_start, effective_user=SimpleNamespace(id=1))
    await learning_handlers.lesson_command(update_start, context)
    state = get_state(context.user_data)
    assert state is not None and state.step == 1 and state.awaiting
    assert msg_start.replies == ["step1?"]

    msg_next = DummyMessage("ans1")
    await learning_handlers.lesson_answer_handler(
        SimpleNamespace(message=msg_next, effective_user=SimpleNamespace(id=1)),
        context,
    )
    state = get_state(context.user_data)
    assert state is not None and state.step == 2 and state.awaiting
    assert msg_next.replies == ["fb", "step2?"]

    msg_idk = DummyMessage("Не знаю")
    await learning_handlers.lesson_answer_handler(
        SimpleNamespace(message=msg_idk, effective_user=SimpleNamespace(id=1)),
        context,
    )
    state = get_state(context.user_data)
    assert state is not None and state.step == 3 and state.awaiting
    assert msg_idk.replies == ["fb", "step3?"]

    msg_next2 = DummyMessage("ans3")
    await learning_handlers.lesson_answer_handler(
        SimpleNamespace(message=msg_next2, effective_user=SimpleNamespace(id=1)),
        context,
    )
    state = get_state(context.user_data)
    assert state is not None and state.step == 4 and state.awaiting
    assert msg_next2.replies == ["fb", "step4?"]

    assert len(lesson_log.pending_logs) == 10
