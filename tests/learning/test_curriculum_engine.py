from __future__ import annotations

import types

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.curriculum_engine import (
    check_answer,
    next_step,
    start_lesson,
)
from services.api.app.diabetes.learning_fixtures import load_lessons
from services.api.app.diabetes.learning_prompts import disclaimer
from services.api.app.diabetes.models_learning import Lesson, LessonProgress, QuizQuestion
from services.api.app.diabetes.services import db, gpt_client


@pytest.mark.asyncio()
async def test_curriculum_flow(monkeypatch: pytest.MonkeyPatch) -> None:
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

    async def fake_completion(**kwargs: object) -> object:
        fake_completion.calls += 1
        return types.SimpleNamespace(
            choices=[
                types.SimpleNamespace(
                    message=types.SimpleNamespace(
                        content=f"text {fake_completion.calls}",
                    )
                )
            ]
        )

    fake_completion.calls = 0  # type: ignore[attr-defined]
    monkeypatch.setattr(
        gpt_client, "create_learning_chat_completion", fake_completion
    )

    progress = await start_lesson(1, slug)
    assert progress.current_step == 0

    step = await next_step(1, lesson_id)
    assert step.startswith(disclaimer())

    for _ in range(2):
        step = await next_step(1, lesson_id)
        assert step
        assert not step.startswith(disclaimer())

    question_text = await next_step(1, lesson_id)
    assert question_text.startswith(disclaimer())

    with db.SessionLocal() as session:
        questions = (
            session.query(QuizQuestion)
            .filter_by(lesson_id=lesson_id)
            .order_by(QuizQuestion.id)
            .all()
        )

    for idx, q in enumerate(questions):
        correct, feedback = await check_answer(1, lesson_id, q.correct_option)
        assert correct is True
        assert feedback
        if idx < len(questions) - 1:
            next_q = await next_step(1, lesson_id)
            assert next_q
            assert not next_q.startswith(disclaimer())

    assert await next_step(1, lesson_id) is None

    with db.SessionLocal() as session:
        progress = (
            session.query(LessonProgress)
            .filter_by(user_id=1, lesson_id=lesson_id)
            .one()
        )
        assert progress.completed is True
        assert progress.quiz_score == 100

