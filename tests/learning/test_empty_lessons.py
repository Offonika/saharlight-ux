from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Mapping

import pytest

from services.api.app.config import settings
from services.api.app.diabetes import learning_handlers
from services.api.app.diabetes.curriculum_engine import LessonNotFoundError
from tests.utils.telegram import make_context, make_update


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(self, text: str, **_: Any) -> None:  # pragma: no cover - helper
        self.replies.append(text)


@pytest.mark.asyncio()
async def test_learn_dynamic_empty_lessons(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dynamic mode should fall back when lessons table is empty."""

    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    async def raise_start_lesson(user_id: int, slug: str) -> SimpleNamespace:
        raise LessonNotFoundError(slug)

    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "start_lesson", raise_start_lesson
    )
    monkeypatch.setattr(learning_handlers, "build_main_keyboard", lambda: None)
    monkeypatch.setattr(learning_handlers, "add_lesson_log", lambda *a, **k: None)
    monkeypatch.setattr(learning_handlers, "disclaimer", lambda: "")
    monkeypatch.setattr(learning_handlers, "choose_initial_topic", lambda _p: ("s", "t"))
    monkeypatch.setattr(learning_handlers, "generate_learning_plan", lambda text: [text])

    async def fake_step(
        profile: Mapping[str, str | None],
        slug: str,
        step_idx: int,
        prev_summary: str | None,
    ) -> str:
        return "step1"

    monkeypatch.setattr(learning_handlers, "generate_step_text", fake_step)
    monkeypatch.setattr(learning_handlers, "ensure_overrides", lambda *_: True)

    msg = DummyMessage()
    update = make_update(message=msg)
    context = make_context(user_data={})

    await learning_handlers.learn_command(update, context)

    assert msg.replies == ["step1"]


@pytest.mark.asyncio()
async def test_learn_static_empty_lessons_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Static mode should automatically fall back to dynamic when no lessons."""

    monkeypatch.setattr(settings, "learning_content_mode", "static")

    async def fake_run_db(fn, *args: object, **kwargs: object) -> bool:
        return False

    monkeypatch.setattr(learning_handlers.db, "run_db", fake_run_db)

    async def raise_start_lesson(user_id: int, slug: str) -> SimpleNamespace:
        raise LessonNotFoundError(slug)

    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "start_lesson", raise_start_lesson
    )
    monkeypatch.setattr(learning_handlers, "build_main_keyboard", lambda: None)
    monkeypatch.setattr(learning_handlers, "add_lesson_log", lambda *a, **k: None)
    monkeypatch.setattr(learning_handlers, "disclaimer", lambda: "")
    monkeypatch.setattr(learning_handlers, "choose_initial_topic", lambda _p: ("s", "t"))
    monkeypatch.setattr(learning_handlers, "generate_learning_plan", lambda text: [text])
    monkeypatch.setattr(learning_handlers, "ensure_overrides", lambda *_: True)

    async def fake_step(
        profile: Mapping[str, str | None],
        slug: str,
        step_idx: int,
        prev_summary: str | None,
    ) -> str:
        return "step1"

    monkeypatch.setattr(learning_handlers, "generate_step_text", fake_step)

    msg = DummyMessage()
    update = make_update(message=msg)
    context = make_context(user_data={})

    await learning_handlers.learn_command(update, context)

    assert msg.replies == ["step1"]
