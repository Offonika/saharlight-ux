from types import SimpleNamespace
from typing import Any

import pytest

from services.api.app.config import settings
from services.api.app.diabetes import learning_handlers
from services.api.app.diabetes.learning_state import LearnState, set_state


class DummyMessage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.from_user = SimpleNamespace(id=1)

    async def reply_text(
        self, text: str, **_: Any
    ) -> None:  # pragma: no cover - helper
        return None


@pytest.mark.asyncio
async def test_lesson_answer_handler_propagates_unexpected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    async def fake_check_user_answer(*_: object, **__: object) -> tuple[bool, str]:
        return True, "feedback"

    async def fake_generate_step_text(*_: object, **__: object) -> str:
        return "next question"

    calls = 0

    async def fail_safe_add_lesson_log(*_: object, **__: object) -> bool:
        nonlocal calls
        calls += 1
        raise ValueError("boom")

    async def ok_hydrate(*_: object, **__: object) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "check_user_answer", fake_check_user_answer)
    monkeypatch.setattr(
        learning_handlers, "generate_step_text", fake_generate_step_text
    )
    monkeypatch.setattr(
        learning_handlers, "safe_add_lesson_log", fail_safe_add_lesson_log
    )
    async def noop_upsert(*_: object, **__: object) -> None:
        return None

    monkeypatch.setattr(
        learning_handlers.progress_repo,
        "upsert_progress",
        noop_upsert,
    )
    monkeypatch.setattr(learning_handlers, "_hydrate", ok_hydrate)
    monkeypatch.setattr(learning_handlers, "_rate_limited", lambda *_a, **_k: False)
    monkeypatch.setattr(learning_handlers, "build_main_keyboard", lambda: None)
    monkeypatch.setattr(learning_handlers, "sanitize_feedback", lambda s: s)
    monkeypatch.setattr(learning_handlers, "format_reply", lambda s: s)
    monkeypatch.setattr(learning_handlers, "ensure_single_question", lambda s: s)

    user_data: dict[str, object] = {}
    set_state(
        user_data, LearnState(topic="t", step=0, awaiting=True, last_step_text="q")
    )
    user_data["learning_plan_id"] = 1

    msg = DummyMessage("ans")
    update = SimpleNamespace(message=msg, effective_user=msg.from_user)
    context = SimpleNamespace(user_data=user_data, bot_data={})

    with pytest.raises(ValueError):
        await learning_handlers.lesson_answer_handler(update, context)

    assert calls == 1


@pytest.mark.asyncio
async def test_lesson_answer_handler_skips_logging_without_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    async def fake_check_user_answer(*_: object, **__: object) -> tuple[bool, str]:
        return True, "feedback"

    async def fake_generate_step_text(*_: object, **__: object) -> str:
        return "next question"

    async def ok_hydrate(*_: object, **__: object) -> bool:
        return True

    called = False

    async def record_safe_add(*_: object, **__: object) -> bool:
        nonlocal called
        called = True
        return True

    monkeypatch.setattr(learning_handlers, "check_user_answer", fake_check_user_answer)
    monkeypatch.setattr(
        learning_handlers, "generate_step_text", fake_generate_step_text
    )
    monkeypatch.setattr(learning_handlers, "safe_add_lesson_log", record_safe_add)
    async def noop_upsert(*_: object, **__: object) -> None:
        return None

    monkeypatch.setattr(
        learning_handlers.progress_repo,
        "upsert_progress",
        noop_upsert,
    )
    monkeypatch.setattr(learning_handlers, "_hydrate", ok_hydrate)
    monkeypatch.setattr(learning_handlers, "_rate_limited", lambda *_a, **_k: False)
    monkeypatch.setattr(learning_handlers, "build_main_keyboard", lambda: None)
    monkeypatch.setattr(learning_handlers, "sanitize_feedback", lambda s: s)
    monkeypatch.setattr(learning_handlers, "format_reply", lambda s: s)
    monkeypatch.setattr(learning_handlers, "ensure_single_question", lambda s: s)

    user_data: dict[str, object] = {}
    set_state(
        user_data, LearnState(topic="t", step=0, awaiting=True, last_step_text="q")
    )

    msg = DummyMessage("ans")
    update = SimpleNamespace(message=msg, effective_user=msg.from_user)
    context = SimpleNamespace(user_data=user_data, bot_data={})

    await learning_handlers.lesson_answer_handler(update, context)

    assert called is False
