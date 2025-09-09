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
    monkeypatch.setattr(dynamic_handlers, "disclaimer", lambda: "")

    async def raise_start_lesson(user_id: int, slug: str) -> object:
        raise LessonNotFoundError(slug)

    monkeypatch.setattr(dynamic_handlers.curriculum_engine, "start_lesson", raise_start_lesson)

    called: dict[str, int] = {"step": 0, "plan": 0, "log": 0}

    async def fake_generate_step_text(
        profile: Mapping[str, str | None],
        slug: str,
        step: int,
        prev_summary: str | None,
    ) -> str:
        called["step"] += 1
        return "step text"

    monkeypatch.setattr(dynamic_handlers, "generate_step_text", fake_generate_step_text)

    def fake_generate_learning_plan(text: str) -> list[str]:
        called["plan"] += 1
        return [f"plan: {text}"]

    monkeypatch.setattr(dynamic_handlers, "generate_learning_plan", fake_generate_learning_plan)
    monkeypatch.setattr(dynamic_handlers, "format_reply", lambda t: t)

    async def fake_add_log(*args: object, **kwargs: object) -> None:
        called["log"] += 1

    monkeypatch.setattr(dynamic_handlers, "add_lesson_log", fake_add_log)

    async def fake_persist(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(dynamic_handlers, "_persist", fake_persist)

    msg = DummyMessage()
    update = make_update(message=msg)
    context = make_context(user_data={})

    await dynamic_handlers.learn_command(update, context)

    assert msg.replies == [
        "Не нашёл учебные записи, пробую динамический режим…",
        "plan: step text",
    ]
    state = get_state(context.user_data)
    assert state is not None
    assert called == {"step": 1, "plan": 1, "log": 1}


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

    called: dict[str, int] = {"step": 0, "plan": 0, "log": 0}

    async def fake_generate_step_text(
        profile: Mapping[str, str | None],
        slug: str,
        step: int,
        prev_summary: str | None,
    ) -> str:
        called["step"] += 1
        return "step text"

    monkeypatch.setattr(dynamic_handlers, "generate_step_text", fake_generate_step_text)

    def fake_generate_learning_plan(text: str) -> list[str]:
        called["plan"] += 1
        return [f"plan: {text}"]

    monkeypatch.setattr(dynamic_handlers, "generate_learning_plan", fake_generate_learning_plan)
    monkeypatch.setattr(dynamic_handlers, "format_reply", lambda t: t)

    async def fake_add_log(*args: object, **kwargs: object) -> None:
        called["log"] += 1

    monkeypatch.setattr(dynamic_handlers, "add_lesson_log", fake_add_log)

    async def fake_persist(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(dynamic_handlers, "_persist", fake_persist)

    msg = DummyMessage()
    update = make_update(message=msg)
    context = make_context(user_data={}, args=["slug"])

    await dynamic_handlers.lesson_command(update, context)

    assert msg.replies == [
        "Не нашёл учебные записи, пробую динамический режим…",
        "plan: step text",
    ]
    state = get_state(context.user_data)
    assert state is not None
    assert called == {"step": 1, "plan": 1, "log": 1}
