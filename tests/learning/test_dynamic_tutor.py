from __future__ import annotations

import pytest

from services.api.app.diabetes import dynamic_tutor


@pytest.mark.asyncio
async def test_step_answer_feedback(monkeypatch: pytest.MonkeyPatch) -> None:
    texts = iter(["step1", "feedback"])

    async def fake_create_learning_chat_completion(**kwargs: object) -> str:
        return next(texts)

    monkeypatch.setattr(
        dynamic_tutor,
        "create_learning_chat_completion",
        fake_create_learning_chat_completion,
    )

    step = await dynamic_tutor.generate_step_text({}, "topic", 1, None)
    correct, feedback = await dynamic_tutor.check_user_answer({}, "topic", "42", step)

    assert step == "step1"
    assert correct is False
    assert feedback == "feedback"


@pytest.mark.asyncio
async def test_runtimeerror_returns_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def raise_runtime_error(**kwargs: object) -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr(dynamic_tutor, "create_learning_chat_completion", raise_runtime_error)

    step = await dynamic_tutor.generate_step_text({}, "topic", 1, None)
    correct, feedback = await dynamic_tutor.check_user_answer({}, "topic", "42", "step")

    assert step == dynamic_tutor.BUSY_MESSAGE
    assert correct is False
    assert feedback == dynamic_tutor.BUSY_MESSAGE
