from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

from services.api.app.config import settings
from services.api.app.diabetes import learning_handlers
from services.api.app.diabetes.learning_state import LearnState


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:  # pragma: no cover - helper
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
        profile: object, topic: str, step_idx: int, prev: object
    ) -> str:
        return "step1"

    monkeypatch.setattr(learning_handlers, "generate_step_text", fake_generate_step_text)

    times = iter([0.0, 1.0])

    def fake_monotonic() -> float:
        try:
            return next(times)
        except StopIteration:
            return 1000.0

    monkeypatch.setattr(learning_handlers.time, "monotonic", fake_monotonic)

    user_data: dict[str, object] = {}

    msg1 = DummyMessage()
    callback1 = DummyCallback(msg1, "lesson:slug")
    update1 = cast(object, SimpleNamespace(callback_query=callback1))
    context1 = SimpleNamespace(user_data=user_data)
    await learning_handlers.lesson_callback(update1, context1)
    assert msg1.replies == ["step1"]

    msg2 = DummyMessage()
    callback2 = DummyCallback(msg2, "lesson:slug")
    update2 = cast(object, SimpleNamespace(callback_query=callback2))
    context2 = SimpleNamespace(user_data=user_data)
    await learning_handlers.lesson_callback(update2, context2)
    assert msg2.replies == [learning_handlers.RATE_LIMIT_MESSAGE]


@pytest.mark.asyncio
async def test_lesson_answer_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")
    async def fake_check_user_answer(
        profile: object, topic: str, answer: str, last: str
    ) -> tuple[bool, str]:
        return True, "feedback"

    async def fake_generate_step_text(
        profile: object, topic: str, step_idx: int, prev: object
    ) -> str:
        return "next"

    monkeypatch.setattr(learning_handlers, "check_user_answer", fake_check_user_answer)
    monkeypatch.setattr(learning_handlers, "generate_step_text", fake_generate_step_text)

    times = iter([0.0, 1.0])

    def fake_monotonic() -> float:
        try:
            return next(times)
        except StopIteration:
            return 1000.0

    monkeypatch.setattr(learning_handlers.time, "monotonic", fake_monotonic)

    user_data: dict[str, object] = {}
    learning_handlers.set_state(
        user_data,
        LearnState(topic="slug", step=1, awaiting_answer=True, last_step_text="q"),
    )

    msg1 = DummyMessage(text="a1")
    update1 = cast(object, SimpleNamespace(message=msg1))
    context1 = SimpleNamespace(user_data=user_data)
    await learning_handlers.lesson_answer_handler(update1, context1)
    assert msg1.replies == ["feedback", "next"]

    msg2 = DummyMessage(text="a2")
    update2 = cast(object, SimpleNamespace(message=msg2))
    context2 = SimpleNamespace(user_data=user_data)
    await learning_handlers.lesson_answer_handler(update2, context2)
    assert msg2.replies == [learning_handlers.RATE_LIMIT_MESSAGE]
