from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from services.api.app.config import settings
from services.api.app.diabetes import learning_handlers
from services.api.app.diabetes.learning_state import LearnState, set_state
from services.api.app.diabetes.llm_router import LLMTask
from services.api.app.assistant.services import progress_service as progress_repo


class DummyMessage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.from_user = SimpleNamespace(id=1)
        self.replies: list[str] = []

    async def reply_text(self, text: str, **_: Any) -> None:  # pragma: no cover - helper
        self.replies.append(text)


@pytest.mark.asyncio
async def test_step_advances_and_text_changes(
    session_local: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Answering a step should advance progress and yield new text."""

    # Deterministic environment
    monkeypatch.setattr(progress_repo, "SessionLocal", session_local, raising=False)
    monkeypatch.setattr(settings, "learning_mode_enabled", True)
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    async def _fake_hydrate(*_a: Any, **_k: Any) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "_hydrate", _fake_hydrate)
    monkeypatch.setattr(learning_handlers, "_rate_limited", lambda *_a, **_k: False)
    monkeypatch.setattr(learning_handlers, "build_main_keyboard", lambda: None)

    # Mock LLM: if prev summary is unsanitized (has double spaces), repeat step
    async def fake_create_learning_chat_completion(
        *, task: LLMTask, messages: list[dict[str, str]], **_: Any
    ) -> str:
        if task is LLMTask.QUIZ_CHECK:
            return "ok"
        user_prompt = next(m["content"] for m in messages if m["role"] == "user")
        if "<b>" in user_prompt:
            return "Шаг 1"
        return "Шаг 2"

    from services.api.app.diabetes import dynamic_tutor

    monkeypatch.setattr(
        dynamic_tutor, "create_learning_chat_completion", fake_create_learning_chat_completion
    )

    async def fake_check_user_answer(*_a: Any, **_k: Any) -> tuple[bool, str]:
        return True, "ответ <b>тест</b>"  # HTML tags will be stripped when sanitized

    monkeypatch.setattr(learning_handlers, "check_user_answer", fake_check_user_answer)

    user_data: dict[str, Any] = {"learning_plan_id": 1}
    set_state(user_data, LearnState(topic="t", step=1, awaiting=True, last_step_text="Шаг 1"))
    await progress_repo.upsert_progress(1, 1, {
        "topic": "t", "module_idx": 0, "step_idx": 1, "snapshot": "Шаг 1", "prev_summary": None,
    })

    msg = DummyMessage("да")
    update = SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data=user_data, bot_data={})

    await learning_handlers.lesson_answer_handler(update, context)

    state = learning_handlers.get_state(user_data)
    assert state.step == 2
    assert state.last_step_text == "Шаг 2"
    progress = await progress_repo.get_progress(1, 1)
    assert progress is not None
    assert progress.progress_json["step_idx"] == 2
