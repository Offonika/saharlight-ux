from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Mapping

import pytest

from services.api.app.config import Settings, settings
from services.api.app.diabetes import curriculum_engine
from services.api.app.diabetes.curriculum_engine import (
    LessonNotFoundError,
    ProgressNotFoundError,
)
from services.api.app.diabetes import learning_handlers as dynamic_handlers
import services.api.app.diabetes.handlers.learning_handlers as handlers
from services.api.app.diabetes.learning_state import get_state
from tests.utils.telegram import make_context, make_update


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
async def test_start_lesson_unknown_slug(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_run_db(fn, *args: object, **kwargs: object) -> object:
        class DummyResult:
            def scalar_one_or_none(self) -> None:
                return None

        class DummySession:
            def execute(
                self, *args: object, **kwargs: object
            ) -> DummyResult:  # pragma: no cover - helper
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
    monkeypatch.setattr(
        dynamic_handlers, "choose_initial_topic", lambda _p: ("slug", "t")
    )
    monkeypatch.setattr(dynamic_handlers, "build_main_keyboard", lambda: None)

    async def fake_step_text(
        profile: Mapping[str, str | None], slug: str, step: int, prev: str | None
    ) -> str:
        return "intro"

    monkeypatch.setattr(dynamic_handlers, "generate_step_text", fake_step_text)
    monkeypatch.setattr(dynamic_handlers, "format_reply", lambda t: t)

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

    monkeypatch.setattr(
        dynamic_handlers.curriculum_engine, "start_lesson", raise_start_lesson
    )

    monkeypatch.setattr(
        dynamic_handlers, "generate_learning_plan", lambda _t: ["step1"]
    )

    async def ok_add_log(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(dynamic_handlers.lesson_log, "safe_add_lesson_log", ok_add_log)

    async def fake_get_active_plan(user_id: int) -> None:
        return None

    async def fake_create_plan(user_id: int, version: int, plan: list[str]) -> int:
        return 1

    async def fake_update_plan(plan_id: int, plan_json: list[str]) -> None:
        return None

    async def fake_upsert_progress(
        user_id: int, plan_id: int, data: Mapping[str, Any]
    ) -> None:
        return None

    monkeypatch.setattr(
        dynamic_handlers.plans_repo, "get_active_plan", fake_get_active_plan
    )
    monkeypatch.setattr(dynamic_handlers.plans_repo, "create_plan", fake_create_plan)
    monkeypatch.setattr(dynamic_handlers.plans_repo, "update_plan", fake_update_plan)
    monkeypatch.setattr(
        dynamic_handlers.progress_repo, "upsert_progress", fake_upsert_progress
    )

    msg = DummyMessage()
    update = make_update(message=msg)
    context = make_context(user_data={})

    await dynamic_handlers.learn_command(update, context)
    assert msg.replies == [
        "\U0001f5fa План обучения\n1. step1",
        "step1",
    ]
    assert get_state(context.user_data) is not None
    assert context.user_data.get("lesson_id") is None


@pytest.mark.asyncio
async def test_lesson_command_lesson_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    async def fake_ensure_overrides(update: object, context: object) -> bool:
        return True

    monkeypatch.setattr(dynamic_handlers, "ensure_overrides", fake_ensure_overrides)
    monkeypatch.setattr(dynamic_handlers, "TOPICS_RU", {"slug": "Topic"})
    monkeypatch.setattr(dynamic_handlers, "build_main_keyboard", lambda: None)
    monkeypatch.setattr(dynamic_handlers, "disclaimer", lambda: "")

    async def fake_step_text(
        profile: Mapping[str, str | None], slug: str, step: int, prev: str | None
    ) -> str:
        return "intro"

    monkeypatch.setattr(dynamic_handlers, "generate_step_text", fake_step_text)
    monkeypatch.setattr(dynamic_handlers, "format_reply", lambda t: t)

    async def raise_start_lesson(user_id: int, slug: str) -> object:
        raise LessonNotFoundError(slug)

    monkeypatch.setattr(
        dynamic_handlers.curriculum_engine, "start_lesson", raise_start_lesson
    )

    async def fail_next_step(
        user_id: int,
        lesson_id: int,
        profile: Mapping[str, str | None],
        prev_summary: str | None = None,
    ) -> tuple[str, bool]:
        raise AssertionError("should not be called")

    monkeypatch.setattr(dynamic_handlers.curriculum_engine, "next_step", fail_next_step)

    monkeypatch.setattr(
        dynamic_handlers, "generate_learning_plan", lambda _t: ["step1"]
    )

    async def ok_add_log(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(dynamic_handlers.lesson_log, "safe_add_lesson_log", ok_add_log)

    async def fake_get_active_plan(user_id: int) -> None:
        return None

    async def fake_create_plan(user_id: int, version: int, plan: list[str]) -> int:
        return 1

    async def fake_update_plan(plan_id: int, plan_json: list[str]) -> None:
        return None

    async def fake_upsert_progress(
        user_id: int, plan_id: int, data: Mapping[str, Any]
    ) -> None:
        return None

    monkeypatch.setattr(
        dynamic_handlers.plans_repo, "get_active_plan", fake_get_active_plan
    )
    monkeypatch.setattr(dynamic_handlers.plans_repo, "create_plan", fake_create_plan)
    monkeypatch.setattr(dynamic_handlers.plans_repo, "update_plan", fake_update_plan)
    monkeypatch.setattr(
        dynamic_handlers.progress_repo, "upsert_progress", fake_upsert_progress
    )

    msg = DummyMessage()
    update = make_update(message=msg)
    context = make_context(user_data={}, args=["slug"])

    await dynamic_handlers.lesson_command(update, context)
    assert msg.replies == [
        "\U0001f5fa План обучения\n1. step1",
        "step1",
    ]
    assert get_state(context.user_data) is not None
    assert context.user_data.get("lesson_id") is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [LessonNotFoundError("slug"), ProgressNotFoundError(1, 1)],
)
async def test_static_lesson_command_next_step_not_found(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    monkeypatch.setattr(
        handlers,
        "settings",
        Settings(
            LEARNING_MODE_ENABLED="1",
            LEARNING_CONTENT_MODE="static",
            _env_file=None,
        ),
    )

    async def fake_ensure_overrides(update: object, context: object) -> bool:
        return True

    monkeypatch.setattr(handlers, "ensure_overrides", fake_ensure_overrides)

    async def ok_start_lesson(user_id: int, slug: str) -> SimpleNamespace:
        return SimpleNamespace(lesson_id=1)

    monkeypatch.setattr(handlers.curriculum_engine, "start_lesson", ok_start_lesson)

    async def raise_next_step(
        user_id: int,
        lesson_id: int,
        profile: Mapping[str, str | None],
        prev_summary: str | None = None,
    ) -> tuple[str, bool]:
        raise error  # type: ignore[misc]

    monkeypatch.setattr(handlers.curriculum_engine, "next_step", raise_next_step)

    msg = DummyMessage()
    update = make_update(message=msg)
    context = make_context(user_data={}, args=["slug"])

    await handlers.lesson_command(update, context)

    assert msg.replies == [handlers.LESSON_NOT_FOUND_MESSAGE]
    assert "lesson_id" not in context.user_data
    assert get_state(context.user_data) is None
