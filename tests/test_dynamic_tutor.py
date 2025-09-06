import asyncio
import types

import pytest

from services.api.app.diabetes import dynamic_tutor


class _FakeCompletion:
    def __init__(self, content: str) -> None:
        self.choices = [
            types.SimpleNamespace(message=types.SimpleNamespace(content=content))
        ]


@pytest.mark.asyncio
async def test_generate_step_text_formats_reply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_create_chat_completion(**kwargs: object) -> _FakeCompletion:
        return _FakeCompletion("a" * 900 + "\n\n" + "b" * 900)

    monkeypatch.setattr(
        dynamic_tutor, "create_chat_completion", fake_create_chat_completion
    )
    monkeypatch.setattr(dynamic_tutor.LLMRouter, "choose_model", lambda self, task: "m")
    monkeypatch.setattr(dynamic_tutor, "log_lesson_turn", lambda *a, **k: asyncio.sleep(0))

    result = await dynamic_tutor.generate_step_text(1, {}, "t", 1, None)

    assert result == "a" * 800 + "\n\n" + "b" * 800


@pytest.mark.asyncio
async def test_generate_step_text_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    async def raise_error(**kwargs: object) -> _FakeCompletion:
        raise RuntimeError("boom")

    monkeypatch.setattr(dynamic_tutor, "create_chat_completion", raise_error)
    monkeypatch.setattr(dynamic_tutor.LLMRouter, "choose_model", lambda self, task: "m")
    monkeypatch.setattr(dynamic_tutor, "log_lesson_turn", lambda *a, **k: asyncio.sleep(0))

    result = await dynamic_tutor.generate_step_text(1, {}, "t", 1, None)

    assert result == "сервер занят, попробуйте позже"


@pytest.mark.asyncio
async def test_check_user_answer_uses_max_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    async def fake_create_chat_completion(**kwargs: object) -> _FakeCompletion:
        captured.update(kwargs)
        return _FakeCompletion("ok")

    monkeypatch.setattr(
        dynamic_tutor, "create_chat_completion", fake_create_chat_completion
    )
    monkeypatch.setattr(dynamic_tutor.LLMRouter, "choose_model", lambda self, task: "m")
    monkeypatch.setattr(dynamic_tutor, "log_lesson_turn", lambda *a, **k: asyncio.sleep(0))

    result = await dynamic_tutor.check_user_answer(1, {}, "topic", 1, "ans", "text")

    assert result == "ok"
    assert captured["max_tokens"] == 250


@pytest.mark.asyncio
async def test_check_user_answer_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    async def raise_error(**kwargs: object) -> _FakeCompletion:
        raise RuntimeError("boom")

    monkeypatch.setattr(dynamic_tutor, "create_chat_completion", raise_error)
    monkeypatch.setattr(dynamic_tutor.LLMRouter, "choose_model", lambda self, task: "m")
    monkeypatch.setattr(dynamic_tutor, "log_lesson_turn", lambda *a, **k: asyncio.sleep(0))

    result = await dynamic_tutor.check_user_answer(1, {}, "topic", 1, "ans", "text")

    assert result == "сервер занят, попробуйте позже"
