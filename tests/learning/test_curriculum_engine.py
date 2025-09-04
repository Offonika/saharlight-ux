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
from services.api.app.diabetes.models_learning import LessonProgress, QuizQuestion
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

    text = await start_lesson(1, 1)
    assert text

    for _ in range(3):
        step = await next_step(1)
        assert step

    with db.SessionLocal() as session:
        answers = [
            q.correct_option
            for q in session.query(QuizQuestion)
            .filter_by(lesson_id=1)
            .order_by(QuizQuestion.id)
        ]

    score = 0
    for ans in answers:
        feedback = await check_answer(1, ans)
        assert feedback
        score += 1
    expected = int(100 * score / len(answers))

    with db.SessionLocal() as session:
        progress = (
            session.query(LessonProgress)
            .filter_by(user_id=1, lesson_id=1)
            .one()
        )
        assert progress.completed is True
        assert progress.quiz_score == expected
