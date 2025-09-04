from __future__ import annotations

from types import SimpleNamespace
from itertools import count
from typing import Any, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from telegram import InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from services.api.app.config import settings
from services.api.app.diabetes.handlers import learning_handlers
from services.api.app.diabetes.learning_fixtures import load_lessons
from services.api.app.diabetes.models_learning import Lesson, QuizQuestion
from services.api.app.diabetes.services import db, gpt_client


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
    return cast(
        Update,
        SimpleNamespace(message=DummyMessage(), effective_user=SimpleNamespace(id=1)),
    )


def make_context(
    *, args: list[str] | None = None, user_data: dict[str, Any] | None = None
) -> CallbackContext[Any, Any, Any, Any]:
    data: dict[str, Any] = {"args": args or [], "user_data": user_data or {}}
    return cast(CallbackContext[Any, Any, Any, Any], SimpleNamespace(**data))


@pytest.mark.asyncio()
async def test_handler_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.SessionLocal.configure(bind=engine)
    db.Base.metadata.create_all(bind=engine)

    await load_lessons(
        "services/api/app/diabetes/content/lessons_v0.json",
        sessionmaker=db.SessionLocal,
    )

    with db.SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id="t1"))
        session.commit()
        lesson = session.query(Lesson).first()
        assert lesson is not None
        slug = lesson.slug
        lesson_id = lesson.id

    monkeypatch.setattr(settings, "learning_enabled", True)
    monkeypatch.setattr(settings, "learning_command_model", "test-model")

    async def fake_completion(**kwargs: object) -> str:
        fake_completion.calls += 1
        return f"text {fake_completion.calls}"

    fake_completion.calls = 0  # type: ignore[attr-defined]
    monkeypatch.setattr(gpt_client, "create_learning_chat_completion", fake_completion)
    times = count(0, 10)
    monkeypatch.setattr(learning_handlers.time, "monotonic", lambda: next(times))

    ctx = make_context()
    upd = make_update()
    await learning_handlers.learn_command(upd, ctx)
    msg = cast(DummyMessage, upd.message)
    assert "Учебный режим активирован" in msg.replies[0]

    ctx.args = [slug]
    upd = make_update()
    await learning_handlers.lesson_command(upd, ctx)
    assert "text 1" in cast(DummyMessage, upd.message).replies[-1]

    for _ in range(2):
        upd = make_update()
        ctx.args = []
        await learning_handlers.lesson_command(upd, ctx)

    upd = make_update()
    ctx.args = []
    await learning_handlers.lesson_command(upd, ctx)
    question_text = cast(DummyMessage, upd.message).replies[-1]
    assert "?" in question_text

    with db.SessionLocal() as session:
        questions = session.query(QuizQuestion).filter_by(lesson_id=lesson_id).all()

    for q in questions:
        upd = make_update()
        ctx.args = [str(q.correct_option)]
        await learning_handlers.quiz_command(upd, ctx)

    assert "Опрос завершён" in cast(DummyMessage, upd.message).replies[-1]

    upd = make_update()
    ctx.args = []
    await learning_handlers.progress_command(upd, ctx)
    progress_reply = cast(DummyMessage, upd.message).replies[0]
    assert str(len(questions)) in progress_reply
    assert "100" in progress_reply
