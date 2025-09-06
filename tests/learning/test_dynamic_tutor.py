from __future__ import annotations

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

    step = await dynamic_tutor.generate_step_text({}, "topic", 1, None)
    correct, feedback = await dynamic_tutor.check_user_answer({}, "topic", "42", step)

    assert step == "step1"
    assert correct is False
    assert feedback == "feedback"


@pytest.mark.asyncio
async def test_runtimeerror_returns_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def raise_runtime_error(**kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(
        dynamic_tutor, "create_chat_completion", raise_runtime_error
    )
    monkeypatch.setattr(dynamic_tutor.LLMRouter, "choose_model", lambda self, task: "m")

    step = await dynamic_tutor.generate_step_text({}, "topic", 1, None)
    correct, feedback = await dynamic_tutor.check_user_answer({}, "topic", "42", "step")

    assert step == "сервер занят, попробуйте позже"
    assert correct is False
    assert feedback == "сервер занят, попробуйте позже"
