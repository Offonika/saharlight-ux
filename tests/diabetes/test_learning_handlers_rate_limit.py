from types import SimpleNamespace
from typing import Any, Mapping, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.config import settings
from services.api.app.diabetes.handlers import learning_handlers


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)


def make_update() -> Update:
    user = SimpleNamespace(id=1)
    return cast(Update, SimpleNamespace(message=DummyMessage(), effective_user=user))


def make_context(**kwargs: Any) -> CallbackContext[Any, Any, Any, Any]:
    data: dict[str, Any] = {"user_data": {}, "args": []}
    data.update(kwargs)
    return cast(CallbackContext[Any, Any, Any, Any], SimpleNamespace(**data))


@pytest.mark.asyncio
async def test_lesson_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)
    async def fake_ensure_overrides(update: object, context: object) -> bool:
        return True

    monkeypatch.setattr(learning_handlers, "ensure_overrides", fake_ensure_overrides)

    calls: list[str] = []

    async def fake_start(user_id: int, slug: str) -> SimpleNamespace:
        calls.append("start")
        return SimpleNamespace(lesson_id=1)

    steps = iter([("step1", False), ("step2", False), (None, True)])

    async def fake_next(
        user_id: int, lesson_id: int, profile: Mapping[str, str | None]
    ) -> tuple[str | None, bool]:
        calls.append("next")
        assert profile == {}
        return next(steps)

    monkeypatch.setattr(learning_handlers.curriculum_engine, "start_lesson", fake_start)
    monkeypatch.setattr(learning_handlers.curriculum_engine, "next_step", fake_next)

    times = iter([0.0, 1.0, 4.0])

    def fake_monotonic() -> float:
        try:
            return next(times)
        except StopIteration:
            return 1000.0

    monkeypatch.setattr(learning_handlers.time, "monotonic", fake_monotonic)

    ctx = make_context(args=["l1"])
    upd1 = make_update()
    await learning_handlers.lesson_command(upd1, ctx)
    msg1 = cast(DummyMessage, upd1.message)
    assert msg1.replies == ["step1"]

    upd2 = make_update()
    ctx2 = make_context(user_data=ctx.user_data, args=[])
    await learning_handlers.lesson_command(upd2, ctx2)
    msg2 = cast(DummyMessage, upd2.message)
    assert msg2.replies == [learning_handlers.RATE_LIMIT_MESSAGE]

    upd3 = make_update()
    ctx3 = make_context(user_data=ctx.user_data, args=[])
    await learning_handlers.lesson_command(upd3, ctx3)
    msg3 = cast(DummyMessage, upd3.message)
    assert msg3.replies == ["step2"]

    assert calls.count("start") == 1
    assert calls.count("next") == 2


@pytest.mark.asyncio
async def test_quiz_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)

    questions = iter([("Q1", False), ("Q2", False), (None, True)])

    async def fake_next(
        user_id: int, lesson_id: int, profile: Mapping[str, str | None]
    ) -> tuple[str | None, bool]:
        assert profile == {}
        return next(questions)

    answers: list[int] = []

    async def fake_check(
        user_id: int,
        lesson_id: int,
        profile: Mapping[str, str | None],
        answer: int,
        last_step_text: str | None = None,
    ) -> tuple[bool, str]:
        assert profile == {}
        answers.append(answer)
        return True, "ok"

    monkeypatch.setattr(learning_handlers.curriculum_engine, "next_step", fake_next)
    monkeypatch.setattr(learning_handlers.curriculum_engine, "check_answer", fake_check)

    times = iter([0.0, 1.0, 4.0])

    def fake_monotonic() -> float:
        try:
            return next(times)
        except StopIteration:
            return 1000.0

    monkeypatch.setattr(learning_handlers.time, "monotonic", fake_monotonic)

    user_data = {"lesson_id": 1}

    upd1 = make_update()
    ctx1 = make_context(user_data=user_data, args=[])
    await learning_handlers.quiz_command(upd1, ctx1)
    msg1 = cast(DummyMessage, upd1.message)
    assert msg1.replies == ["Q1"]

    upd2 = make_update()
    ctx2 = make_context(user_data=user_data, args=["1"])
    await learning_handlers.quiz_command(upd2, ctx2)
    msg2 = cast(DummyMessage, upd2.message)
    assert msg2.replies == [learning_handlers.RATE_LIMIT_MESSAGE]
    assert answers == []

    upd3 = make_update()
    ctx3 = make_context(user_data=user_data, args=["1"])
    await learning_handlers.quiz_command(upd3, ctx3)
    msg3 = cast(DummyMessage, upd3.message)
    assert msg3.replies == ["ok", "Q2"]
    assert answers == [1]
