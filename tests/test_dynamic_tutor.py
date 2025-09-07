import pytest

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
async def test_generate_step_text_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    async def raise_error(**kwargs: object) -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr(
        dynamic_tutor, "create_learning_chat_completion", raise_error
    )

    result = await dynamic_tutor.generate_step_text({}, "t", 1, None)

    assert result == "сервер занят, попробуйте позже"


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
async def test_check_user_answer_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    async def raise_error(**kwargs: object) -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr(
        dynamic_tutor, "create_learning_chat_completion", raise_error
    )

    correct, result = await dynamic_tutor.check_user_answer({}, "topic", "ans", "text")

    assert correct is False
    assert result == "сервер занят, попробуйте позже"

