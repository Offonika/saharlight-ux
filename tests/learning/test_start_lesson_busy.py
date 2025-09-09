from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from services.api.app.diabetes import learning_handlers
from services.api.app.diabetes.dynamic_tutor import BUSY_MESSAGE


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []
        self.from_user = SimpleNamespace(id=1)

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)


@pytest.mark.asyncio
async def test_start_lesson_busy_message(monkeypatch: pytest.MonkeyPatch) -> None:
    async def raise_start_lesson(user_id: int, slug: str) -> object:
        raise learning_handlers.curriculum_engine.LessonNotFoundError(slug)

    async def fake_generate_step_text(*_a: object, **_k: object) -> str:
        return BUSY_MESSAGE

    monkeypatch.setattr(learning_handlers.curriculum_engine, "start_lesson", raise_start_lesson)
    monkeypatch.setattr(learning_handlers, "generate_step_text", fake_generate_step_text)
    monkeypatch.setattr(learning_handlers, "disclaimer", lambda: "DISCLAIMER")
    monkeypatch.setattr(
        learning_handlers,
        "generate_learning_plan",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("should not be called")),
    )

    msg = DummyMessage()
    user_data: dict[str, object] = {}
    bot_data: dict[str, object] = {}

    await learning_handlers._start_lesson(msg, user_data, bot_data, {}, "slug")
    assert msg.replies == [BUSY_MESSAGE]
    assert "lesson_id" not in user_data
