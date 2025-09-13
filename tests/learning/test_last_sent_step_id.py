import pytest
from types import SimpleNamespace
from typing import Any

from services.api.app.diabetes import learning_handlers
from services.api.app.diabetes.models_learning import ProgressData


class DummyMessage:
    """Minimal Telegram-like message collecting replies and IDs."""

    counter = 0

    def __init__(self, text: str = "", user_id: int = 1) -> None:
        self.text = text
        self.from_user = SimpleNamespace(id=user_id)
        self.sent: list[str] = []

    async def reply_text(self, text: str, **_kwargs: Any) -> SimpleNamespace:
        DummyMessage.counter += 1
        self.sent.append(text)
        return SimpleNamespace(message_id=DummyMessage.counter)


@pytest.mark.asyncio
async def test_last_sent_step_id_updates(monkeypatch: pytest.MonkeyPatch) -> None:
    """ID of the last sent step is stored and updated on new step."""

    monkeypatch.setattr(learning_handlers.settings, "learning_mode_enabled", True)
    monkeypatch.setattr(learning_handlers.settings, "learning_content_mode", "dynamic")
    monkeypatch.setattr(learning_handlers, "build_main_keyboard", lambda: None)
    monkeypatch.setattr(learning_handlers, "disclaimer", lambda: "")
    monkeypatch.setattr(learning_handlers, "format_reply", lambda t: t)
    monkeypatch.setattr(learning_handlers, "ensure_single_question", lambda t: t)
    monkeypatch.setattr(learning_handlers, "sanitize_feedback", lambda t: t)
    async def fake_get_profile(_uid: int) -> None:
        return None

    monkeypatch.setattr(learning_handlers, "get_learning_profile", fake_get_profile)
    monkeypatch.setattr(learning_handlers, "assistant_chat", lambda *_a, **_k: "fb")

    async def fake_start_lesson(user_id: int, slug: str) -> SimpleNamespace:
        return SimpleNamespace(lesson_id=1)

    async def fake_next_step(
        user_id: int, lesson_id: int, profile: Any, prev: str | None = None
    ) -> tuple[str, bool]:
        fake_next_step.calls += 1
        return f"step {fake_next_step.calls}", False

    fake_next_step.calls = 0
    monkeypatch.setattr(learning_handlers.curriculum_engine, "start_lesson", fake_start_lesson)
    monkeypatch.setattr(learning_handlers.curriculum_engine, "next_step", fake_next_step)
    monkeypatch.setattr(learning_handlers, "generate_learning_plan", lambda text: [text])
    monkeypatch.setattr(learning_handlers, "pretty_plan", lambda plan: "1. " + plan[0])

    async def fake_add_log(*_a: object, **_k: object) -> None:
        return None

    monkeypatch.setattr(learning_handlers, "safe_add_lesson_log", fake_add_log)

    async def fake_get_active_plan(_uid: int) -> None:
        return None

    async def fake_create_plan(_uid: int, _version: int, _plan: list[str]) -> int:
        return 1

    async def fake_update_plan(plan_id: int, plan_json: list[str]) -> None:
        return None

    monkeypatch.setattr(learning_handlers.plans_repo, "get_active_plan", fake_get_active_plan)
    monkeypatch.setattr(learning_handlers.plans_repo, "create_plan", fake_create_plan)
    monkeypatch.setattr(learning_handlers.plans_repo, "update_plan", fake_update_plan)

    calls: list[ProgressData] = []

    async def spy_upsert(uid: int, pid: int, data: ProgressData) -> None:
        calls.append(data.copy())

    monkeypatch.setattr(learning_handlers.progress_repo, "upsert_progress", spy_upsert)

    user_data: dict[str, Any] = {}
    bot_data: dict[str, object] = {}

    msg1 = DummyMessage()
    await learning_handlers._start_lesson(msg1, user_data, bot_data, {}, "intro")

    assert calls[0]["last_sent_step_id"] == 2
    progress_map = bot_data[learning_handlers.PROGRESS_KEY]
    assert progress_map[1]["last_sent_step_id"] == 2

    context = SimpleNamespace(user_data=user_data, bot_data=bot_data)
    msg2 = DummyMessage(text="answer")
    update = SimpleNamespace(message=msg2, effective_user=msg2.from_user)
    await learning_handlers.lesson_answer_handler(update, context)

    assert calls[-1]["last_sent_step_id"] == 3
    assert progress_map[1]["last_sent_step_id"] == 3
