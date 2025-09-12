import pytest
from types import SimpleNamespace
from typing import Any, Mapping

from tests.utils.telegram import make_context, make_update

from services.api.app.config import settings
from services.api.app.diabetes import learning_handlers
from services.api.app.diabetes.learning_state import LearnState, set_state
from telegram.ext import ApplicationHandlerStop


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.from_user = SimpleNamespace(id=1)
        self.replies: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)


@pytest.mark.asyncio
async def test_on_any_text_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")
    user_data: dict[str, object] = {}
    set_state(
        user_data, LearnState(topic="t", step=1, awaiting=True, last_step_text="q")
    )
    called = False

    async def fake_check_user_answer(
        profile: Mapping[str, str | None], topic: str, answer: str, last: str
    ) -> tuple[bool, str]:
        nonlocal called
        called = True
        assert answer == "ans"
        assert last == "q"
        return True, "fb"

    async def fake_generate_step_text(
        profile: Mapping[str, str | None], topic: str, step_idx: int, prev: object
    ) -> str:
        return "next"

    monkeypatch.setattr(learning_handlers, "check_user_answer", fake_check_user_answer)
    monkeypatch.setattr(
        learning_handlers, "generate_step_text", fake_generate_step_text
    )

    async def fake_add_log(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(learning_handlers, "safe_add_lesson_log", fake_add_log)
    monkeypatch.setattr(learning_handlers, "format_reply", lambda t: t)

    msg = DummyMessage("ans")
    update = make_update(message=msg)
    context = make_context(user_data=user_data)

    with pytest.raises(ApplicationHandlerStop):
        await learning_handlers.on_any_text(update, context)
    assert called
    assert msg.replies == ["fb\n\n—\n\nnext"]


@pytest.mark.asyncio
async def test_on_any_text_idontknow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")
    user_data: dict[str, object] = {}
    set_state(
        user_data,
        LearnState(topic="t", step=1, awaiting=True, last_step_text="q"),
    )
    called = False

    async def fake_assistant_chat(profile: Mapping[str, str | None], text: str) -> str:
        nonlocal called
        called = True
        assert "q" in text
        return "fb"

    async def fake_generate_step_text(
        profile: Mapping[str, str | None], topic: str, step_idx: int, prev: object
    ) -> str:
        assert prev == "fb"
        return "next"

    async def fake_check_user_answer(
        *args: object, **kwargs: object
    ) -> tuple[bool, str]:
        raise AssertionError("should not be called")

    async def fake_add_log(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(learning_handlers, "assistant_chat", fake_assistant_chat)
    monkeypatch.setattr(
        learning_handlers, "generate_step_text", fake_generate_step_text
    )
    monkeypatch.setattr(learning_handlers, "check_user_answer", fake_check_user_answer)
    monkeypatch.setattr(learning_handlers, "safe_add_lesson_log", fake_add_log)
    monkeypatch.setattr(learning_handlers, "format_reply", lambda t: t)

    msg = DummyMessage("Не знаю")
    update = make_update(message=msg)
    context = make_context(user_data=user_data)

    with pytest.raises(ApplicationHandlerStop):
        await learning_handlers.on_any_text(update, context)
    assert called
    assert msg.replies == ["fb\n\n—\n\nnext"]


@pytest.mark.asyncio
async def test_on_any_text_general(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")
    user_data: dict[str, object] = {}
    called = False

    async def fake_assistant_chat(profile: Mapping[str, str | None], text: str) -> str:
        nonlocal called
        called = True
        assert text == "hello"
        return "reply"

    async def fake_check_user_answer(
        *args: object, **kwargs: object
    ) -> tuple[bool, str]:
        raise AssertionError("should not be called")

    monkeypatch.setattr(learning_handlers, "assistant_chat", fake_assistant_chat)
    monkeypatch.setattr(learning_handlers, "check_user_answer", fake_check_user_answer)
    monkeypatch.setattr(learning_handlers, "format_reply", lambda t: t)

    msg = DummyMessage("hello")
    update = make_update(message=msg)
    context = make_context(user_data=user_data)

    with pytest.raises(ApplicationHandlerStop):
        await learning_handlers.on_any_text(update, context)
    assert called
    assert msg.replies == ["reply"]


@pytest.mark.asyncio
async def test_on_any_text_within_grace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")
    monkeypatch.setattr(learning_handlers.time, "monotonic", lambda: 1000.0)
    user_data: dict[str, object] = {}
    set_state(
        user_data,
        LearnState(
            topic="t",
            step=1,
            awaiting=False,
            last_step_text="q",
            last_step_at=1000.0 - learning_handlers.STEP_GRACE_PERIOD + 1,
        ),
    )
    called = False

    async def fake_check_user_answer(
        profile: Mapping[str, str | None], topic: str, answer: str, last: str
    ) -> tuple[bool, str]:
        nonlocal called
        called = True
        return True, "fb"

    async def fake_generate_step_text(
        profile: Mapping[str, str | None], topic: str, step_idx: int, prev: object
    ) -> str:
        return "next"

    monkeypatch.setattr(learning_handlers, "check_user_answer", fake_check_user_answer)
    monkeypatch.setattr(
        learning_handlers, "generate_step_text", fake_generate_step_text
    )

    async def fake_add_log(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(learning_handlers, "safe_add_lesson_log", fake_add_log)
    monkeypatch.setattr(learning_handlers, "format_reply", lambda t: t)

    msg = DummyMessage("ans")
    update = make_update(message=msg)
    context = make_context(user_data=user_data)

    with pytest.raises(ApplicationHandlerStop):
        await learning_handlers.on_any_text(update, context)
    assert called
    assert msg.replies == ["fb\n\n—\n\nnext"]
