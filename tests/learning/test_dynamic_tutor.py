from __future__ import annotations

import asyncio

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

    monkeypatch.setattr(
        dynamic_tutor, "create_learning_chat_completion", raise_runtime_error
    )

    step = await dynamic_tutor.generate_step_text({}, "topic", 1, None)
    correct, feedback = await dynamic_tutor.check_user_answer({}, "topic", "42", "step")

    assert step == dynamic_tutor.BUSY_MESSAGE
    assert correct is False
    assert feedback == dynamic_tutor.BUSY_MESSAGE


@pytest.mark.asyncio
async def test_cancellation_not_suppressed(monkeypatch: pytest.MonkeyPatch) -> None:
    async def raise_cancelled(**kwargs: object) -> str:
        raise asyncio.CancelledError()

    monkeypatch.setattr(
        dynamic_tutor, "create_learning_chat_completion", raise_cancelled
    )

    with pytest.raises(asyncio.CancelledError):
        await dynamic_tutor.generate_step_text({}, "topic", 1, None)
    with pytest.raises(asyncio.CancelledError):
        await dynamic_tutor.check_user_answer({}, "topic", "42", "step")


@pytest.mark.asyncio
async def test_sanitize_feedback_strips_questions(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_create_learning_chat_completion(**kwargs: object) -> str:
        return "✅ Всё понятно? Повтори? Третье?"

    monkeypatch.setattr(
        dynamic_tutor,
        "create_learning_chat_completion",
        fake_create_learning_chat_completion,
    )

    _, feedback = await dynamic_tutor.check_user_answer({}, "t", "a", "s")

    assert "?" not in feedback
    assert feedback.startswith("✅")


@pytest.mark.asyncio
async def test_sanitize_feedback_limits_sentences_and_length(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    long_tail = "вторая" * 200
    text = f"⚠️ первая. {long_tail}. третья лишняя."  # three sentences

    async def fake_create_learning_chat_completion(**kwargs: object) -> str:
        return text

    monkeypatch.setattr(
        dynamic_tutor,
        "create_learning_chat_completion",
        fake_create_learning_chat_completion,
    )

    _, feedback = await dynamic_tutor.check_user_answer({}, "t", "a", "s")

    assert "третья" not in feedback
    assert len(feedback) <= 400
