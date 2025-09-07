import logging

import pytest
from openai import OpenAIError

from services.api.app.diabetes import dynamic_tutor


@pytest.mark.asyncio
async def test_generate_step_text_formats_reply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_create_learning_chat_completion(**kwargs: object) -> str:
        return "a" * 800 + "\n\n" + "b" * 800

    monkeypatch.setattr(
        dynamic_tutor,
        "create_learning_chat_completion",
        fake_create_learning_chat_completion,
    )

    result = await dynamic_tutor.generate_step_text({}, "t", 1, None)

    assert result == "a" * 800 + "\n\n" + "b" * 800


@pytest.mark.asyncio
async def test_generate_step_text_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def raise_error(**kwargs: object) -> str:
        raise OpenAIError("boom")

    monkeypatch.setattr(dynamic_tutor, "create_learning_chat_completion", raise_error)

    result = await dynamic_tutor.generate_step_text({}, "t", 1, None)

    assert result == dynamic_tutor.BUSY_MESSAGE


@pytest.mark.asyncio
async def test_generate_step_text_unexpected_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def raise_error(**kwargs: object) -> str:
        raise ValueError("boom")

    monkeypatch.setattr(dynamic_tutor, "create_learning_chat_completion", raise_error)

    with pytest.raises(ValueError):
        await dynamic_tutor.generate_step_text({}, "t", 1, None)


@pytest.mark.asyncio
async def test_check_user_answer_uses_max_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_create_learning_chat_completion(**kwargs: object) -> str:
        captured.update(kwargs)
        return "ok"

    monkeypatch.setattr(
        dynamic_tutor,
        "create_learning_chat_completion",
        fake_create_learning_chat_completion,
    )

    correct, result = await dynamic_tutor.check_user_answer({}, "topic", "ans", "text")

    assert correct is False
    assert result == "ok"
    assert captured["max_tokens"] == 250


@pytest.mark.asyncio
async def test_check_user_answer_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def raise_error(**kwargs: object) -> str:
        raise OpenAIError("boom")

    monkeypatch.setattr(dynamic_tutor, "create_learning_chat_completion", raise_error)

    correct, result = await dynamic_tutor.check_user_answer({}, "topic", "ans", "text")

    assert correct is False
    assert result == dynamic_tutor.BUSY_MESSAGE


@pytest.mark.asyncio
async def test_check_user_answer_unexpected_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def raise_error(**kwargs: object) -> str:
        raise ValueError("boom")

    monkeypatch.setattr(dynamic_tutor, "create_learning_chat_completion", raise_error)

    with pytest.raises(ValueError):
        await dynamic_tutor.check_user_answer({}, "topic", "ans", "text")


@pytest.mark.asyncio
async def test_check_user_answer_empty_feedback(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    async def fake_create_learning_chat_completion(**kwargs: object) -> str:
        return "   "

    monkeypatch.setattr(
        dynamic_tutor,
        "create_learning_chat_completion",
        fake_create_learning_chat_completion,
    )

    with caplog.at_level(logging.WARNING):
        correct, result = await dynamic_tutor.check_user_answer(
            {}, "topic", "ans", "text"
        )

    assert correct is False
    assert result == dynamic_tutor.BUSY_MESSAGE
    assert "empty feedback" in caplog.text
