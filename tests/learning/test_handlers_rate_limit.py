from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from services.api.app.config import settings
from services.api.app.diabetes import learning_handlers
from services.api.app.diabetes.learning_state import LearnState
from tests.utils.telegram import make_context, make_update


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.replies: list[str] = []
        self.from_user = SimpleNamespace(id=1)

    async def reply_text(
        self, text: str, **kwargs: Any
    ) -> None:  # pragma: no cover - helper
        self.replies.append(text)


class DummyCallback:
    def __init__(self, message: DummyMessage, data: str) -> None:
        self.message = message
        self.data = data
        self.answered = False

    async def answer(self) -> None:  # pragma: no cover - helper
        self.answered = True


@pytest.mark.asyncio
async def test_lesson_callback_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    async def fake_generate_step_text(
        profile: object,
        topic: str,
        step_idx: int,
        prev: object,
        *,
        user_id: int | None = None,
    ) -> str:
        return "step1"

    monkeypatch.setattr(
        learning_handlers, "generate_step_text", fake_generate_step_text
    )
    monkeypatch.setattr(learning_handlers, "TOPICS_RU", {"slug": "Topic"})

    async def fake_start_lesson(user_id: int, topic_slug: str) -> object:
        return SimpleNamespace(lesson_id=1)

    async def fake_next_step(
        user_id: int,
        lesson_id: int,
        profile: object,
        prev_summary: str | None = None,
    ) -> tuple[str, bool]:
        return "step1", False

    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "start_lesson", fake_start_lesson
    )
    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "next_step", fake_next_step
    )
    monkeypatch.setattr(learning_handlers, "disclaimer", lambda: "")

    times = iter([0.0, 0.0, 1.0, 1.0])

    def fake_monotonic() -> float:
        try:
            return next(times)
        except StopIteration:
            return 1000.0

    monkeypatch.setattr(learning_handlers.time, "monotonic", fake_monotonic)

    user_data: dict[str, object] = {}

    msg1 = DummyMessage()
    callback1 = DummyCallback(msg1, "lesson:slug")
    update1 = make_update(callback_query=callback1)
    context1 = make_context(user_data=user_data)
    await learning_handlers.lesson_callback(update1, context1)
    plan = learning_handlers.generate_learning_plan("step1")
    assert msg1.replies == [
        f"\U0001f5fa План обучения\n{learning_handlers.pretty_plan(plan)}",
        "step1",
    ]

    msg2 = DummyMessage()
    callback2 = DummyCallback(msg2, "lesson:slug")
    update2 = make_update(callback_query=callback2)
    context2 = make_context(user_data=user_data)
    await learning_handlers.lesson_callback(update2, context2)
    assert msg2.replies == [learning_handlers.RATE_LIMIT_MESSAGE]


@pytest.mark.asyncio
async def test_lesson_answer_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    async def _noop(*_a: object, **_k: object) -> None:
        return None

    monkeypatch.setattr(learning_handlers, "safe_add_lesson_log", _noop)
    monkeypatch.setattr(learning_handlers, "_rate_limited", lambda *_args, **_kw: True)

    user_data: dict[str, object] = {}
    learning_handlers.set_state(
        user_data,
        LearnState(topic="slug", step=1, awaiting=True, last_step_text="q"),
    )

    msg = DummyMessage(text="a2")
    update = make_update(message=msg)
    context = make_context(user_data=user_data)
    await learning_handlers.lesson_answer_handler(update, context)
    assert msg.replies == [learning_handlers.RATE_LIMIT_MESSAGE]
