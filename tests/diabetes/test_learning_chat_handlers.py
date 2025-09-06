
from types import SimpleNamespace
from typing import Any, Mapping, cast

import pytest
from telegram import InlineKeyboardMarkup, ReplyKeyboardMarkup

from services.api.app.config import settings
from services.api.app.diabetes import learning_handlers
from services.api.app.diabetes.learning_state import LearnState, get_state, set_state


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.from_user = SimpleNamespace(id=1)
        self.replies: list[str] = []
        self.markups: list[InlineKeyboardMarkup | None] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:  # pragma: no cover - helper
        self.replies.append(text)
        self.markups.append(cast(InlineKeyboardMarkup | None, kwargs.get("reply_markup")))


class DummyCallback:
    def __init__(self, message: DummyMessage, data: str) -> None:
        self.message = message
        self.data = data
        self.answered = False

    async def answer(self) -> None:  # pragma: no cover - helper
        self.answered = True


@pytest.mark.asyncio
async def test_learn_command_and_callback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")
    monkeypatch.setattr(settings, "learning_ui_show_topics", True)
    async def fake_ensure_overrides(update: object, context: object) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "ensure_overrides", fake_ensure_overrides)
    monkeypatch.setattr(learning_handlers, "TOPICS_RU", {"slug": "Topic"})
    async def fake_generate_step_text(*args: object, **kwargs: object) -> str:
        return "step1?"
    monkeypatch.setattr(learning_handlers, "generate_step_text", fake_generate_step_text)
    async def fake_add_log(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(learning_handlers, "add_lesson_log", fake_add_log)

    msg = DummyMessage()
    update = cast(object, SimpleNamespace(message=msg))
    context = SimpleNamespace(user_data={})

    await learning_handlers.learn_command(update, context)
    assert isinstance(msg.markups[0], ReplyKeyboardMarkup)
    inline_markup = msg.markups[1]
    assert isinstance(inline_markup, InlineKeyboardMarkup)
    assert inline_markup.inline_keyboard[0][0].callback_data == "lesson:slug"

    msg2 = DummyMessage()
    query = DummyCallback(msg2, "lesson:slug")
    update_cb = cast(object, SimpleNamespace(callback_query=query))
    context_cb = SimpleNamespace(user_data={})

    await learning_handlers.lesson_callback(update_cb, context_cb)
    assert msg2.replies == ["step1?"]
    assert isinstance(msg2.markups[0], ReplyKeyboardMarkup)
    state = get_state(context_cb.user_data)
    assert state is not None and state.step == 1 and state.awaiting_answer


@pytest.mark.asyncio
async def test_lesson_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")
    async def fake_generate_step_text(
        profile: object, topic: str, step_idx: int, prev: object
    ) -> str:
        return f"step{step_idx}?"

    async def fake_check_user_answer(
        profile: object, topic: str, answer: str, last: str
    ) -> str:
        return "feedback"

    monkeypatch.setattr(learning_handlers, "generate_step_text", fake_generate_step_text)
    monkeypatch.setattr(learning_handlers, "check_user_answer", fake_check_user_answer)
    async def fake_add_log(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(learning_handlers, "add_lesson_log", fake_add_log)

    msg = DummyMessage()
    update = cast(object, SimpleNamespace(message=msg))
    context = SimpleNamespace(user_data={}, args=["slug"])

    await learning_handlers.lesson_command(update, context)
    assert msg.replies == ["step1?"]
    assert isinstance(msg.markups[0], ReplyKeyboardMarkup)

    msg2 = DummyMessage(text="ans")
    update2 = cast(object, SimpleNamespace(message=msg2))
    context2 = SimpleNamespace(user_data=context.user_data)

    await learning_handlers.lesson_answer_handler(update2, context2)
    assert msg2.replies == ["feedback", "step2?"]
    assert all(isinstance(m, ReplyKeyboardMarkup) for m in msg2.markups)
    state = get_state(context2.user_data)
    assert state is not None and state.step == 2 and state.awaiting_answer


@pytest.mark.asyncio
async def test_exit_command_clears_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")
    msg = DummyMessage()
    update = cast(object, SimpleNamespace(message=msg))
    user_data: dict[str, Any] = {}
    set_state(user_data, LearnState("t", 1, True))
    context = SimpleNamespace(user_data=user_data)

    await learning_handlers.exit_command(update, context)
    assert msg.replies == ["Учебная сессия завершена."]
    assert isinstance(msg.markups[0], ReplyKeyboardMarkup)
    assert get_state(user_data) is None


@pytest.mark.asyncio
async def test_learn_command_autostarts_when_topics_hidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")
    monkeypatch.setattr(settings, "learning_ui_show_topics", False)

    async def fake_ensure_overrides(update: object, context: object) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "ensure_overrides", fake_ensure_overrides)
    monkeypatch.setattr(
        learning_handlers, "choose_initial_topic", lambda _: ("slug", "t")
    )

    progress = SimpleNamespace(lesson_id=1)
    async def fake_start_lesson(user_id: int, slug: str) -> object:
        assert slug == "slug"
        return progress

    async def fake_next_step(
        user_id: int,
        lesson_id: int,
        profile: Mapping[str, str | None],
        prev_summary: str | None = None,
    ) -> tuple[str, bool]:
        assert lesson_id == 1
        assert profile == {}
        assert prev_summary is None
        return "first", False

    monkeypatch.setattr(learning_handlers, "format_reply", lambda t: t)
    monkeypatch.setattr(learning_handlers.curriculum_engine, "start_lesson", fake_start_lesson)
    monkeypatch.setattr(learning_handlers.curriculum_engine, "next_step", fake_next_step)
    async def fake_add_log(*args: object, **kwargs: object) -> None:
        return None
    monkeypatch.setattr(learning_handlers, "add_lesson_log", fake_add_log)

    msg = DummyMessage()
    update = cast(object, SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=7)))
    context = SimpleNamespace(user_data={})

    await learning_handlers.learn_command(update, context)
    assert msg.replies == ["first"]
    assert isinstance(msg.markups[0], ReplyKeyboardMarkup)
    state = get_state(context.user_data)
    assert state is not None and state.topic == "slug" and state.step == 1
