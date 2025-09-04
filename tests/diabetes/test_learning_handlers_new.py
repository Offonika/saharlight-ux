from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from services.api.app.config import settings
from services.api.app.diabetes import learning_handlers


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []
        self.reply_markup: InlineKeyboardMarkup | None = None

    async def reply_text(
        self, text: str, reply_markup: InlineKeyboardMarkup | None = None
    ) -> None:
        self.replies.append(text)
        if reply_markup is not None:
            self.reply_markup = reply_markup


def make_update() -> Update:
    return cast(Update, SimpleNamespace(message=DummyMessage(), effective_user=SimpleNamespace(id=1)))


def make_context(**kwargs: Any) -> CallbackContext[Any, Any, Any, Any]:
    data = {"user_data": {}, "args": []}
    data.update(kwargs)
    return cast(CallbackContext[Any, Any, Any, Any], SimpleNamespace(**data))


@pytest.mark.asyncio
async def test_disabled_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", False)
    for handler in [
        learning_handlers.learn_command,
        learning_handlers.lesson_command,
        learning_handlers.quiz_command,
        learning_handlers.progress_command,
        learning_handlers.exit_command,
    ]:
        upd = make_update()
        ctx = make_context()
        await handler(upd, ctx)
        msg = cast(DummyMessage, upd.message)
        assert msg.replies == [learning_handlers.DISABLED_TEXT]


@pytest.mark.asyncio
async def test_learn_lists_lessons(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)
    lessons = [SimpleNamespace(title=f"L{i}", slug=f"l{i}") for i in range(1, 4)]

    async def fake_run_db(fn: Any, *a: Any, **kw: Any) -> list[Any]:
        return lessons

    monkeypatch.setattr(learning_handlers.db, "run_db", fake_run_db)
    upd = make_update()
    ctx = make_context()
    await learning_handlers.learn_command(upd, ctx)
    msg = cast(DummyMessage, upd.message)
    assert msg.reply_markup is not None
    buttons = [b.text for row in msg.reply_markup.inline_keyboard for b in row]
    assert buttons == ["L1", "L2", "L3"]


@pytest.mark.asyncio
async def test_lesson_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)
    calls: list[str] = []

    async def fake_start(user_id: int, slug: str) -> SimpleNamespace:
        calls.append(f"start:{slug}")
        return SimpleNamespace(lesson_id=1)

    steps = iter(["step1", "step2"])

    async def fake_next(user_id: int, lesson_id: int) -> str | None:
        calls.append("next")
        return next(steps, None)

    monkeypatch.setattr(learning_handlers.curriculum_engine, "start_lesson", fake_start)
    monkeypatch.setattr(learning_handlers.curriculum_engine, "next_step", fake_next)
    progress = SimpleNamespace(current_step=1, quiz_score=0)
    lesson = SimpleNamespace(title="L1")

    async def fake_fetch(user_id: int, lesson_id: int) -> tuple[Any, Any]:
        return progress, lesson

    monkeypatch.setattr(learning_handlers, "_fetch_progress", fake_fetch)

    upd = make_update()
    ctx = make_context(args=["l1"])
    await learning_handlers.lesson_command(upd, ctx)
    msg = cast(DummyMessage, upd.message)
    assert msg.replies == ["step1"]
    assert ctx.user_data["lesson_id"] == 1

    upd2 = make_update()
    ctx2 = make_context(user_data=ctx.user_data, args=[])
    await learning_handlers.lesson_command(upd2, ctx2)
    msg2 = cast(DummyMessage, upd2.message)
    assert msg2.replies == ["step2"]
    assert calls.count("start:l1") == 1
    assert calls.count("next") == 2


@pytest.mark.asyncio
async def test_quiz(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)
    questions = iter(["Q1", None])

    async def fake_next(user_id: int, lesson_id: int) -> str | None:
        return next(questions, None)

    async def fake_check(user_id: int, lesson_id: int, answer: int) -> tuple[bool, str]:
        return True, "ok"

    monkeypatch.setattr(learning_handlers.curriculum_engine, "next_step", fake_next)
    monkeypatch.setattr(learning_handlers.curriculum_engine, "check_answer", fake_check)

    upd = make_update()
    ctx = make_context(user_data={"lesson_id": 1})
    await learning_handlers.quiz_command(upd, ctx)
    msg = cast(DummyMessage, upd.message)
    assert msg.replies == ["Q1"]

    upd2 = make_update()
    ctx2 = make_context(user_data={"lesson_id": 1}, args=["0"])
    await learning_handlers.quiz_command(upd2, ctx2)
    msg2 = cast(DummyMessage, upd2.message)
    assert msg2.replies == ["ok", "Опрос завершён"]


@pytest.mark.asyncio
async def test_progress(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)
    progress = SimpleNamespace(current_step=2, quiz_score=50)
    lesson = SimpleNamespace(title="L1")

    async def fake_run_db(fn: Any, *a: Any, **kw: Any) -> tuple[Any, Any]:
        return progress, lesson

    monkeypatch.setattr(learning_handlers.db, "run_db", fake_run_db)
    upd = make_update()
    ctx = make_context(user_data={"lesson_id": 1})
    await learning_handlers.progress_command(upd, ctx)
    msg = cast(DummyMessage, upd.message)
    assert "L1" in msg.replies[0]
    assert "2" in msg.replies[0]
    assert "50" in msg.replies[0]


@pytest.mark.asyncio
async def test_lesson_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)

    async def fake_fetch(user_id: int, lesson_id: int) -> tuple[Any | None, Any | None]:
        return None, None

    monkeypatch.setattr(learning_handlers, "_fetch_progress", fake_fetch)
    upd = make_update()
    ctx = make_context(user_data={"lesson_id": 1})
    await learning_handlers.lesson_command(upd, ctx)
    msg = cast(DummyMessage, upd.message)
    assert msg.replies == ["Урок не найден"]


@pytest.mark.asyncio
async def test_progress_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)

    async def fake_fetch(user_id: int, lesson_id: int) -> tuple[Any | None, Any | None]:
        return None, None

    monkeypatch.setattr(learning_handlers, "_fetch_progress", fake_fetch)
    upd = make_update()
    ctx = make_context(user_data={"lesson_id": 1})
    await learning_handlers.progress_command(upd, ctx)
    msg = cast(DummyMessage, upd.message)
    assert msg.replies == ["Урок не найден"]


@pytest.mark.asyncio
async def test_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_mode_enabled", True)
    upd = make_update()
    ctx = make_context(user_data={"lesson_id": 1})
    await learning_handlers.exit_command(upd, ctx)
    msg = cast(DummyMessage, upd.message)
    assert msg.replies == ["Вы вышли из учебного режима"]
    assert ctx.user_data == {}
