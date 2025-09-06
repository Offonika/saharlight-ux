from __future__ import annotations

import pytest
from prometheus_client import CollectorRegistry, Counter, Summary
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.curriculum_engine import (
    check_answer,
    next_step,
    start_lesson,
)
from services.api.app.config import settings
from services.api.app.diabetes.learning_fixtures import load_lessons
from services.api.app.diabetes.models_learning import (
    Lesson,
    LessonProgress,
    LessonStep,
    QuizQuestion,
)
from services.api.app.diabetes.services import db, gpt_client


@pytest.mark.asyncio
async def test_lesson_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    """Complete a lesson and ensure Prometheus counters track activity."""
    monkeypatch.setattr(settings, "learning_content_mode", "static")
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    db.SessionLocal.configure(bind=engine)
    db.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(settings, "learning_content_mode", "static")

    await load_lessons(
        "content/lessons_v0.json",
        sessionmaker=db.SessionLocal,
    )

    with db.SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id="t1"))
        session.commit()
        lesson = session.query(Lesson).first()
        assert lesson is not None
        slug = lesson.slug
        lesson_id = lesson.id
        step_count = session.query(LessonStep).filter_by(lesson_id=lesson_id).count()
        questions = session.query(QuizQuestion).filter_by(lesson_id=lesson_id).order_by(QuizQuestion.id).all()

    async def fake_completion(**kwargs: object) -> str:
        return "text"

    monkeypatch.setattr(gpt_client, "create_learning_chat_completion", fake_completion)

    registry = CollectorRegistry()
    lessons_started = Counter("lessons_started", "", registry=registry)
    lessons_completed = Counter("lessons_completed", "", registry=registry)
    quiz_avg_score = Summary("quiz_avg_score", "", registry=registry)

    lessons_started.inc()
    await start_lesson(1, slug)

    for _ in range(step_count):
        text, completed = await next_step(1, lesson_id, {})
        assert text is not None
        assert completed is False
    text, completed = await next_step(1, lesson_id, {})
    assert text is not None
    assert completed is False

    for idx, q in enumerate(questions):
        await check_answer(1, lesson_id, q.correct_option + 1)
        text, completed = await next_step(1, lesson_id, {})
        if idx < len(questions) - 1:
            assert text is not None
            assert completed is False

    text, completed = await next_step(1, lesson_id, {})
    assert text is None
    assert completed is True
    lessons_completed.inc()

    with db.SessionLocal() as session:
        progress = session.query(LessonProgress).filter_by(user_id=1, lesson_id=lesson_id).one()
    quiz_avg_score.observe(progress.quiz_score or 0)

    assert registry.get_sample_value("lessons_started_total") == 1.0
    assert registry.get_sample_value("lessons_completed_total") == 1.0
    sum_val = registry.get_sample_value("quiz_avg_score_sum") or 0.0
    count_val = registry.get_sample_value("quiz_avg_score_count") or 1.0
    assert sum_val / count_val == progress.quiz_score
