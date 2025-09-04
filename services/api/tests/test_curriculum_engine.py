from __future__ import annotations

import types

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.services import db
from services.api.app.diabetes.models_learning import (
    Lesson,
    LessonProgress,
    LessonStep,
    QuizQuestion,
)
from services.api.app.diabetes import curriculum_engine
from services.api.app.diabetes.curriculum_engine import (
    start_lesson,
    next_step,
    check_answer,
)
from services.api.app.diabetes.services.db import run_db


class DummyChoice:  # helper for fake LLM response
    def __init__(self, content: str) -> None:
        self.message = types.SimpleNamespace(content=content)


class DummyCompletion:
    def __init__(self, content: str) -> None:
        self.choices = [DummyChoice(content)]


@pytest.mark.asyncio()
async def test_curriculum_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)

    # patch module sessionmaker and llm client
    monkeypatch.setattr(curriculum_engine, "SessionLocal", SessionLocal)

    async def fake_completion(*args, **kwargs):  # type: ignore[no-untyped-def]
        return DummyCompletion("llm")

    monkeypatch.setattr(
        curriculum_engine, "create_learning_chat_completion", fake_completion
    )

    with SessionLocal() as session:
        user = db.User(telegram_id=1, thread_id="t")
        lesson = Lesson(title="Intro", slug="intro", content="Basics")
        session.add_all([user, lesson])
        session.flush()
        session.add_all(
            [
                LessonStep(lesson_id=lesson.id, step_order=1, content="s1"),
                LessonStep(lesson_id=lesson.id, step_order=2, content="s2"),
            ]
        )
        session.add_all(
            [
                QuizQuestion(
                    lesson_id=lesson.id,
                    question="q1",
                    options=["a", "b"],
                    correct_option=0,
                ),
                QuizQuestion(
                    lesson_id=lesson.id,
                    question="q2",
                    options=["c", "d"],
                    correct_option=1,
                ),
            ]
        )
        session.commit()

    progress = await start_lesson(1, "intro")
    assert progress.current_step == 0

    text = await next_step(1, progress.lesson_id)
    assert text == "llm"

    def _fetch(session: Session, /) -> LessonProgress:
        obj = session.get(LessonProgress, progress.id)
        assert obj is not None
        return obj

    progress = await run_db(_fetch, sessionmaker=SessionLocal)
    assert progress.current_step == 1

    await next_step(1, progress.lesson_id)  # second step
    question_text = await next_step(1, progress.lesson_id)
    assert question_text is not None and "q1" in question_text

    ok, msg = await check_answer(1, progress.lesson_id, 0)
    assert ok is True and msg == "llm"

    progress = await run_db(_fetch, sessionmaker=SessionLocal)
    assert progress.quiz_score == 1
    assert progress.current_question == 1

    question_text = await next_step(1, progress.lesson_id)
    assert question_text is not None and "q2" in question_text
    ok, _ = await check_answer(1, progress.lesson_id, 0)
    assert ok is False

    progress = await run_db(_fetch, sessionmaker=SessionLocal)
    assert progress.completed is True and progress.quiz_score == 1
    assert await next_step(1, progress.lesson_id) is None
