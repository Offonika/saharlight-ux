from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.curriculum_engine import (
    check_answer,
    next_step,
    start_lesson,
)
from services.api.app.diabetes.learning_fixtures import load_lessons
from services.api.app.diabetes.prompts import LESSONS_V0_PATH, disclaimer
from services.api.app.diabetes.models_learning import Lesson, LessonProgress, QuizQuestion
from services.api.app.diabetes.services import db, gpt_client
from services.api.app.config import settings


@pytest.mark.asyncio()
async def test_happy_path_one_lesson(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "learning_content_mode", "static")
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.SessionLocal.configure(bind=engine)
    db.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(settings, "learning_content_mode", "static")

    await load_lessons(
        LESSONS_V0_PATH,
        sessionmaker=db.SessionLocal,
    )

    with db.SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id="t1"))
        session.commit()
        lesson = session.query(Lesson).first()
        assert lesson is not None
        slug = lesson.slug
        lesson_id = lesson.id

    async def fake_completion(**kwargs: object) -> str:
        fake_completion.calls += 1
        return f"text {fake_completion.calls}"

    fake_completion.calls = 0  # type: ignore[attr-defined]
    monkeypatch.setattr(gpt_client, "create_learning_chat_completion", fake_completion)

    progress = await start_lesson(1, slug)
    assert progress.current_step == 0

    text, completed = await next_step(1, lesson_id, {})
    assert text == f"{disclaimer()}\n\ntext 1"
    assert completed is False
    text, completed = await next_step(1, lesson_id, {})
    assert text == "text 2"
    assert completed is False
    text, completed = await next_step(1, lesson_id, {})
    assert text == "text 3"
    assert completed is False

    question_text, completed = await next_step(1, lesson_id, {})
    assert completed is False
    assert question_text and question_text.startswith(disclaimer())

    with db.SessionLocal() as session:
        questions = session.query(QuizQuestion).filter_by(lesson_id=lesson_id).all()

    first_opts = "\n".join(f"{idx}. {opt}" for idx, opt in enumerate(questions[0].options, start=1))
    assert question_text.endswith(first_opts)

    for idx, q in enumerate(questions):
        correct, feedback = await check_answer(1, lesson_id, {}, q.correct_option + 1)
        assert correct is True
        assert feedback
        text, completed = await next_step(1, lesson_id, {})
        if idx < len(questions) - 1:
            assert text
            assert completed is False

    text, completed = await next_step(1, lesson_id, {})
    assert text is None
    assert completed is True

    with db.SessionLocal() as session:
        prog = session.query(LessonProgress).filter_by(user_id=1, lesson_id=lesson_id).one()
        assert prog.completed is True
        assert prog.quiz_score == 100
