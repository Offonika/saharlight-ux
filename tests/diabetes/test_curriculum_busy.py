from types import SimpleNamespace
from typing import Any, Mapping

import pytest

from services.api.app.config import settings
from services.api.app.diabetes import learning_handlers as dynamic_handlers
from services.api.app.diabetes.dynamic_tutor import BUSY_MESSAGE
from services.api.app.diabetes.learning_state import get_state
from tests.utils.telegram import make_context, make_update

legacy_handlers = dynamic_handlers


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.from_user = SimpleNamespace(id=1)
        self.replies: list[str] = []
        self.markups: list[Any] = []

    async def reply_text(
        self, text: str, **kwargs: Any
    ) -> None:  # pragma: no cover - helper
        self.replies.append(text)
        self.markups.append(kwargs.get("reply_markup"))


@pytest.mark.asyncio
async def test_dynamic_learn_command_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    async def fake_ensure_overrides(update: object, context: object) -> bool:
        return True

    monkeypatch.setattr(dynamic_handlers, "ensure_overrides", fake_ensure_overrides)
    monkeypatch.setattr(
        dynamic_handlers, "choose_initial_topic", lambda _profile: ("slug", "t")
    )

    async def fake_start_lesson(user_id: int, slug: str) -> object:
        return SimpleNamespace(lesson_id=1)

    async def fake_next_step(
        user_id: int,
        lesson_id: int,
        profile: Mapping[str, str | None],
        prev_summary: str | None = None,
    ) -> tuple[str, bool]:
        return BUSY_MESSAGE, False

    monkeypatch.setattr(
        dynamic_handlers.curriculum_engine, "start_lesson", fake_start_lesson
    )
    monkeypatch.setattr(dynamic_handlers.curriculum_engine, "next_step", fake_next_step)

    def fail_generate_learning_plan(_text: str) -> list[str]:
        raise AssertionError("should not be called")

    monkeypatch.setattr(
        dynamic_handlers, "generate_learning_plan", fail_generate_learning_plan
    )

    async def fail_add_log(*args: object, **kwargs: object) -> None:
        raise AssertionError("should not be called")

    monkeypatch.setattr(dynamic_handlers, "safe_add_lesson_log", fail_add_log)

    msg = DummyMessage()
    update = make_update(message=msg)
    context = make_context(user_data={})

    await dynamic_handlers.learn_command(update, context)

    assert msg.replies == [BUSY_MESSAGE]
    assert get_state(context.user_data) is None
    assert context.user_data.get("lesson_id") is None


@pytest.mark.asyncio
async def test_legacy_lesson_command_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)
    monkeypatch.setattr(settings, "learning_content_mode", "static")

    async def fake_start(user_id: int, slug: str) -> object:
        return SimpleNamespace(lesson_id=1)

    async def fake_next(
        user_id: int, lesson_id: int, profile: Mapping[str, str | None]
    ) -> tuple[str, bool]:
        return BUSY_MESSAGE, False

    monkeypatch.setattr(legacy_handlers.curriculum_engine, "start_lesson", fake_start)
    monkeypatch.setattr(legacy_handlers.curriculum_engine, "next_step", fake_next)

    async def fake_ensure_overrides(update: object, context: object) -> bool:
        return True

    monkeypatch.setattr(legacy_handlers, "ensure_overrides", fake_ensure_overrides)

    msg = DummyMessage()
    update = make_update(message=msg)
    context = make_context(user_data={}, args=["slug"])

    await legacy_handlers.lesson_command(update, context)

    assert msg.replies == [BUSY_MESSAGE]
    assert get_state(context.user_data) is None
    assert context.user_data.get("lesson_id") is None
