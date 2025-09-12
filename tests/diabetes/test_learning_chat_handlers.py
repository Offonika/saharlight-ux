from types import SimpleNamespace
from typing import Any, Mapping, cast

import asyncio
import pytest
from sqlalchemy.exc import SQLAlchemyError
from telegram import InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import CallbackContext

from services.api.app.config import settings
from services.api.app.diabetes import dynamic_tutor, learning_handlers
from services.api.app.diabetes.prompts import disclaimer
from services.api.app.diabetes.learning_state import LearnState, get_state, set_state
from services.api.app.ui.keyboard import LEARN_BUTTON_TEXT
from services.api.app.diabetes.planner import generate_learning_plan, pretty_plan


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.from_user = SimpleNamespace(id=1)
        self.replies: list[str] = []
        self.markups: list[InlineKeyboardMarkup | None] = []

    async def reply_text(
        self, text: str, **kwargs: Any
    ) -> None:  # pragma: no cover - helper
        self.replies.append(text)
        self.markups.append(
            cast(InlineKeyboardMarkup | None, kwargs.get("reply_markup"))
        )


class DummyCallback:
    def __init__(self, message: DummyMessage, data: str) -> None:
        self.message = message
        self.data = data
        self.answered = False

    async def answer(self) -> None:  # pragma: no cover - helper
        self.answered = True


def make_update(
    *,
    message: object | None = None,
    callback_query: object | None = None,
    user_id: int = 1,
) -> Update:
    user = SimpleNamespace(id=user_id)
    data: dict[str, Any] = {"effective_user": user}
    if message is not None:
        data["message"] = message
    if callback_query is not None:
        data["callback_query"] = callback_query
    return cast(Update, SimpleNamespace(**data))


def make_context(
    *,
    user_data: dict[str, Any] | None = None,
    bot_data: dict[str, Any] | None = None,
    args: list[str] | None = None,
) -> CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]]:
    data = {
        "user_data": user_data or {},
        "bot_data": bot_data or {},
        "args": args or [],
    }
    return cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(**data),
    )


@pytest.mark.asyncio
async def test_learn_command_and_callback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")
    monkeypatch.setattr(settings, "learning_ui_show_topics", True)

    async def fake_ensure_overrides(update: object, context: object) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "ensure_overrides", fake_ensure_overrides)
    monkeypatch.setattr(learning_handlers, "TOPICS_RU", {"slug": "Topic"})
    monkeypatch.setattr(learning_handlers, "TOPICS_RU", {"slug": "Topic"})
    monkeypatch.setattr(learning_handlers, "TOPICS_RU", {"slug": "Topic"})

    async def fake_start_lesson(user_id: int, slug: str) -> SimpleNamespace:
        return SimpleNamespace(lesson_id=1)

    async def fake_next_step(
        user_id: int,
        lesson_id: int,
        profile: Mapping[str, str | None],
        prev_summary: str | None = None,
    ) -> tuple[str, bool]:
        return f"{disclaimer()}\n\nstep1?", False

    async def fake_add_log(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "start_lesson", fake_start_lesson
    )
    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "next_step", fake_next_step
    )
    monkeypatch.setattr(learning_handlers, "safe_add_lesson_log", fake_add_log)

    msg = DummyMessage()
    update = make_update(message=msg)
    context = make_context(user_data={})

    await learning_handlers.learn_command(update, context)
    assert isinstance(msg.markups[0], ReplyKeyboardMarkup)
    inline_markup = msg.markups[1]
    assert isinstance(inline_markup, InlineKeyboardMarkup)
    assert inline_markup.inline_keyboard[0][0].callback_data == "lesson:slug"

    msg2 = DummyMessage()
    query = DummyCallback(msg2, "lesson:slug")
    update_cb = make_update(callback_query=query)
    context_cb = make_context(user_data={})

    await learning_handlers.lesson_callback(update_cb, context_cb)
    plan = learning_handlers.generate_learning_plan(f"{disclaimer()}\n\nstep1?")
    assert msg2.replies == [
        f"\U0001f5fa План обучения\n{learning_handlers.pretty_plan(plan)}",
        f"{disclaimer()}\n\nstep1?",
    ]
    assert isinstance(msg2.markups[0], ReplyKeyboardMarkup)
    state = get_state(context_cb.user_data)
    assert state is not None and state.step == 1 and state.awaiting


@pytest.mark.asyncio
async def test_lesson_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    async def fake_check_user_answer(
        profile: object, topic: str, answer: str, last: str
    ) -> tuple[bool, str]:
        return True, "feedback"

    monkeypatch.setattr(learning_handlers, "check_user_answer", fake_check_user_answer)

    async def fake_add_log(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(learning_handlers, "safe_add_lesson_log", fake_add_log)

    async def fake_ensure_overrides(update: object, context: object) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "ensure_overrides", fake_ensure_overrides)
    monkeypatch.setattr(learning_handlers, "TOPICS_RU", {"slug": "Topic"})

    async def fake_start_lesson(user_id: int, slug: str) -> SimpleNamespace:
        return SimpleNamespace(lesson_id=1)

    steps_iter = iter(["step1?", "step2?"])

    async def fake_next_step(
        user_id: int,
        lesson_id: int,
        profile: Mapping[str, str | None],
        prev_summary: str | None = None,
    ) -> tuple[str, bool]:
        text = next(steps_iter)
        if prev_summary is None and text == "step1?":
            return f"{disclaimer()}\n\n{text}", False
        return text, False

    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "start_lesson", fake_start_lesson
    )
    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "next_step", fake_next_step
    )

    msg = DummyMessage()
    update = make_update(message=msg)
    context = make_context(user_data={}, args=["slug"])

    await learning_handlers.lesson_command(update, context)
    expected_plan = generate_learning_plan(f"{disclaimer()}\n\nstep1?")
    plan_text = f"\U0001f5fa План обучения\n{pretty_plan(expected_plan)}"
    assert msg.replies == [plan_text, f"{disclaimer()}\n\nstep1?"]
    assert isinstance(msg.markups[0], ReplyKeyboardMarkup)

    msg2 = DummyMessage(text="ans")
    update2 = make_update(message=msg2)
    context2 = make_context(user_data=context.user_data)

    await learning_handlers.lesson_answer_handler(update2, context2)
    assert msg2.replies == ["feedback\n\n—\n\nstep2?"]
    assert all(isinstance(m, ReplyKeyboardMarkup) for m in msg2.markups)
    state = get_state(context2.user_data)
    assert state is not None and state.step == 2 and state.awaiting


@pytest.mark.asyncio
async def test_lesson_command_unknown_topic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")
    monkeypatch.setattr(learning_handlers, "TOPICS_RU", {"known": "Topic"})

    async def fake_ensure_overrides(update: object, context: object) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "ensure_overrides", fake_ensure_overrides)

    called = False

    async def fake_start_lesson(*args: object, **kwargs: object) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(learning_handlers, "_start_lesson", fake_start_lesson)

    msg = DummyMessage()
    update = make_update(message=msg)
    context = make_context(user_data={}, args=["unknown"])

    await learning_handlers.lesson_command(update, context)

    assert msg.replies == ["Неизвестная тема"]
    assert called is False


@pytest.mark.asyncio
async def test_lesson_callback_unknown_topic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")
    monkeypatch.setattr(learning_handlers, "TOPICS_RU", {"known": "Topic"})

    called = False

    async def fake_start_lesson(*args: object, **kwargs: object) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(learning_handlers, "_start_lesson", fake_start_lesson)

    msg = DummyMessage()
    query = DummyCallback(msg, "lesson:unknown")
    update = make_update(callback_query=query)
    context = make_context(user_data={})

    await learning_handlers.lesson_callback(update, context)

    assert query.answered is True
    assert msg.replies == ["Неизвестная тема"]
    assert called is False


@pytest.mark.asyncio
async def test_exit_command_clears_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")
    msg = DummyMessage()
    update = make_update(message=msg)
    user_data: dict[str, Any] = {}
    set_state(user_data, LearnState(topic="t", step=1, awaiting=True))
    context = make_context(user_data=user_data)

    await learning_handlers.exit_command(update, context)
    assert msg.replies == [f"Сессия {LEARN_BUTTON_TEXT} завершена."]
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
    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "start_lesson", fake_start_lesson
    )
    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "next_step", fake_next_step
    )

    async def fake_add_log(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(learning_handlers, "safe_add_lesson_log", fake_add_log)

    msg = DummyMessage()
    update = make_update(message=msg, user_id=7)
    context = make_context(user_data={})

    await learning_handlers.learn_command(update, context)
    plan = learning_handlers.generate_learning_plan("first")
    assert msg.replies == [
        f"\U0001f5fa План обучения\n{learning_handlers.pretty_plan(plan)}",
        "first",
    ]
    assert isinstance(msg.markups[0], ReplyKeyboardMarkup)
    state = get_state(context.user_data)
    assert state is not None and state.topic == "slug" and state.step == 1


@pytest.mark.asyncio
async def test_lesson_answer_ignores_busy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")
    msg = DummyMessage(text="ans")
    user_data: dict[str, Any] = {"learn_busy": True}
    set_state(
        user_data,
        LearnState(topic="slug", step=1, last_step_text="q", awaiting=True),
    )
    update = make_update(message=msg)
    context = make_context(user_data=user_data)

    await learning_handlers.lesson_answer_handler(update, context)

    assert msg.replies == []


@pytest.mark.asyncio
async def test_lesson_answer_double_click(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    async def slow_check_user_answer(
        profile: object, topic: str, answer: str, last: str
    ) -> tuple[bool, str]:
        await asyncio.sleep(0)
        return True, "fb"

    async def fake_generate_step_text(
        profile: object, topic: str, step_idx: int, prev: object
    ) -> str:
        return "next"

    monkeypatch.setattr(learning_handlers, "check_user_answer", slow_check_user_answer)
    monkeypatch.setattr(
        learning_handlers, "generate_step_text", fake_generate_step_text
    )

    async def fake_add_log(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(learning_handlers, "safe_add_lesson_log", fake_add_log)
    monkeypatch.setattr(learning_handlers, "format_reply", lambda t: t)

    user_data: dict[str, Any] = {}
    set_state(
        user_data,
        LearnState(topic="slug", step=1, last_step_text="q", awaiting=True),
    )

    msg1 = DummyMessage("ans")
    update1 = make_update(message=msg1)
    context1 = make_context(user_data=user_data)

    task = asyncio.create_task(
        learning_handlers.lesson_answer_handler(update1, context1)
    )
    await asyncio.sleep(0)

    msg2 = DummyMessage("ans")
    update2 = make_update(message=msg2)
    context2 = make_context(user_data=user_data)
    await learning_handlers.lesson_answer_handler(update2, context2)
    await task

    assert msg1.replies == ["fb\n\n—\n\nnext"]
    assert msg2.replies == []


@pytest.mark.asyncio
async def test_lesson_answer_handler_error_keeps_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    async def fake_check_user_answer(
        *args: object, **kwargs: object
    ) -> tuple[bool, str]:
        return False, dynamic_tutor.BUSY_MESSAGE

    async def fail_generate_step_text(*args: object, **kwargs: object) -> str:
        raise AssertionError("should not be called")

    monkeypatch.setattr(learning_handlers, "check_user_answer", fake_check_user_answer)
    monkeypatch.setattr(
        learning_handlers, "generate_step_text", fail_generate_step_text
    )

    async def fake_add_log(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(learning_handlers, "safe_add_lesson_log", fake_add_log)

    msg = DummyMessage(text="ans")
    user_data: dict[str, Any] = {}
    set_state(
        user_data,
        LearnState(topic="slug", step=1, last_step_text="q", awaiting=True),
    )
    update = make_update(message=msg)
    context = make_context(user_data=user_data)

    await learning_handlers.lesson_answer_handler(update, context)

    assert msg.replies == [dynamic_tutor.BUSY_MESSAGE]
    state = get_state(user_data)
    assert state is not None
    assert state.step == 1
    assert state.awaiting
    assert not context.user_data.get("learn_busy", False)


@pytest.mark.asyncio
async def test_lesson_answer_handler_add_log_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "dynamic")

    async def fail_add_log(*args: object, **kwargs: object) -> None:
        raise SQLAlchemyError("db error")

    calls: list[tuple[object, ...]] = []

    async def fake_check_user_answer(
        *args: object, **kwargs: object
    ) -> tuple[bool, str]:
        calls.append(args)
        return True, "feedback"

    monkeypatch.setattr(learning_handlers, "safe_add_lesson_log", fail_add_log)
    monkeypatch.setattr(learning_handlers, "check_user_answer", fake_check_user_answer)

    async def fake_generate_step_text(*_a: object, **_k: object) -> str:
        return "step2"

    monkeypatch.setattr(
        learning_handlers, "generate_step_text", fake_generate_step_text
    )

    async def fake_next_step(
        user_id: int,
        lesson_id: int,
        profile: Mapping[str, str | None],
        prev_summary: str | None = None,
    ) -> tuple[str, bool]:
        return "step2", False

    monkeypatch.setattr(
        learning_handlers.curriculum_engine, "next_step", fake_next_step
    )
    monkeypatch.setattr(learning_handlers, "format_reply", lambda t: t)
    monkeypatch.setattr(learning_handlers, "disclaimer", lambda: "")

    msg = DummyMessage(text="ans")
    user_data: dict[str, Any] = {}
    set_state(
        user_data,
        LearnState(topic="slug", step=1, last_step_text="q", awaiting=True),
    )
    update = make_update(message=msg)
    context = make_context(user_data=user_data)

    await learning_handlers.lesson_answer_handler(update, context)
    assert calls, "check_user_answer should be called"
    assert msg.replies == ["feedback\n\n—\n\nstep2"]
    state = get_state(user_data)
    assert state is not None
    assert state.step == 2
    assert state.awaiting
    assert not context.user_data.get("learn_busy", False)
