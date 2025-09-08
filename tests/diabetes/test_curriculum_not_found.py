from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Mapping

import pytest

from services.api.app.config import settings
from services.api.app.diabetes import curriculum_engine
from services.api.app.diabetes.curriculum_engine import LessonNotFoundError
from services.api.app.diabetes import learning_handlers as dynamic_handlers
from services.api.app.diabetes.learning_state import get_state
from tests.utils.telegram import make_context, make_update


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.from_user = SimpleNamespace(id=1)
        self.replies: list[str] = []
        self.markups: list[Any] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:  # pragma: no cover - helper
        self.replies.append(text)
        self.markups.append(kwargs.get("reply_markup"))


@pytest.mark.asyncio
async def test_start_lesson_unknown_slug(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_run_db(fn, *args: object, **kwargs: object) -> object:
        class DummyResult:
            def scalar_one_or_none(self) -> None:
                return None

        class DummySession:
            def execute(self, *args: object, **kwargs: object) -> DummyResult:  # pragma: no cover - helper
                return DummyResult()

        return fn(DummySession())

    monkeypatch.setattr(curriculum_engine.db, "run_db", fake_run_db)

    with pytest.raises(LessonNotFoundError) as excinfo:
        await curriculum_engine.start_lesson(1, "missing")

    assert "missing" in str(excinfo.value)


@pytest.mark.asyncio
async def test_learn_command_lesson_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    async def fake_ensure_overrides(update: object, context: object) -> bool:
        return True

    monkeypatch.setattr(dynamic_handlers, "ensure_overrides", fake_ensure_overrides)
    monkeypatch.setattr(dynamic_handlers, "choose_initial_topic", lambda _p: ("slug", "t"))
    monkeypatch.setattr(dynamic_handlers, "build_main_keyboard", lambda: None)

    async def fail_next_step(
        user_id: int,
        lesson_id: int,
        profile: Mapping[str, str | None],
        prev_summary: str | None = None,
    ) -> tuple[str, bool]:
        raise AssertionError("should not be called")

    monkeypatch.setattr(dynamic_handlers.curriculum_engine, "next_step", fail_next_step)

    async def raise_start_lesson(user_id: int, slug: str) -> object:
        raise LessonNotFoundError(slug)

    monkeypatch.setattr(dynamic_handlers.curriculum_engine, "start_lesson", raise_start_lesson)

    def fail_generate_learning_plan(_text: str) -> list[str]:
        raise AssertionError("should not be called")

    monkeypatch.setattr(dynamic_handlers, "generate_learning_plan", fail_generate_learning_plan)

    async def fail_add_log(*args: object, **kwargs: object) -> None:
        raise AssertionError("should not be called")

    monkeypatch.setattr(dynamic_handlers, "add_lesson_log", fail_add_log)

    msg = DummyMessage()
    update = make_update(message=msg)
    context = make_context(user_data={})

    await dynamic_handlers.learn_command(update, context)

    assert msg.replies == [dynamic_handlers.LESSON_NOT_FOUND_MESSAGE]
    assert get_state(context.user_data) is None


@pytest.mark.asyncio
async def test_lesson_command_lesson_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    async def fake_ensure_overrides(update: object, context: object) -> bool:
        return True

    monkeypatch.setattr(dynamic_handlers, "ensure_overrides", fake_ensure_overrides)
    monkeypatch.setattr(dynamic_handlers, "TOPICS_RU", {"slug": "Topic"})
    monkeypatch.setattr(dynamic_handlers, "build_main_keyboard", lambda: None)
    monkeypatch.setattr(dynamic_handlers, "disclaimer", lambda: "")

    async def raise_start_lesson(user_id: int, slug: str) -> object:
        raise LessonNotFoundError(slug)

    monkeypatch.setattr(dynamic_handlers.curriculum_engine, "start_lesson", raise_start_lesson)

    async def fail_next_step(
        user_id: int,
        lesson_id: int,
        profile: Mapping[str, str | None],
        prev_summary: str | None = None,
    ) -> tuple[str, bool]:
        raise AssertionError("should not be called")

    monkeypatch.setattr(dynamic_handlers.curriculum_engine, "next_step", fail_next_step)

    def fail_generate_learning_plan(_text: str) -> list[str]:
        raise AssertionError("should not be called")

    monkeypatch.setattr(dynamic_handlers, "generate_learning_plan", fail_generate_learning_plan)

    async def fail_add_log(*args: object, **kwargs: object) -> None:
        raise AssertionError("should not be called")

    monkeypatch.setattr(dynamic_handlers, "add_lesson_log", fail_add_log)

    msg = DummyMessage()
    update = make_update(message=msg)
    context = make_context(user_data={}, args=["slug"])

    await dynamic_handlers.lesson_command(update, context)

    assert msg.replies == [dynamic_handlers.LESSON_NOT_FOUND_MESSAGE]
    assert get_state(context.user_data) is None
