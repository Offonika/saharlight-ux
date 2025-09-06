from __future__ import annotations

import asyncio
import types

import pytest

from services.api.app.diabetes import dynamic_tutor


class _FakeCompletion:
    def __init__(self, text: str) -> None:
        self.choices = [
            types.SimpleNamespace(message=types.SimpleNamespace(content=text))
        ]


@pytest.mark.asyncio
async def test_step_answer_feedback(monkeypatch: pytest.MonkeyPatch) -> None:
    texts = iter(["step1", "feedback"])

    async def fake_create_chat_completion(**kwargs: object) -> _FakeCompletion:
        return _FakeCompletion(next(texts))

    monkeypatch.setattr(dynamic_tutor, "create_chat_completion", fake_create_chat_completion)
    monkeypatch.setattr(dynamic_tutor.LLMRouter, "choose_model", lambda self, task: "m")
    monkeypatch.setattr(dynamic_tutor, "log_lesson_turn", lambda *a, **k: asyncio.sleep(0))

    step = await dynamic_tutor.generate_step_text(1, {}, "topic", 1, None)
    feedback = await dynamic_tutor.check_user_answer(1, {}, "topic", 1, "42", step)

    assert step == "step1"
    assert feedback == "feedback"
