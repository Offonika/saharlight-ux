import logging

import pytest
from prometheus_client import CollectorRegistry, Counter
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes import curriculum_engine
from services.api.app.diabetes.curriculum_engine import check_answer, start_lesson
from services.api.app.diabetes.learning_fixtures import load_lessons
from services.api.app.diabetes.models_learning import Lesson, QuizQuestion
from services.api.app.diabetes.services import db, gpt_client


@pytest.mark.asyncio()
async def test_lesson_logging_and_metrics(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
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
        questions = session.query(QuizQuestion).filter_by(lesson_id=lesson_id).order_by(QuizQuestion.id).all()

    async def fake_completion(**kwargs: object) -> str:
        return "text"

    monkeypatch.setattr(gpt_client, "create_learning_chat_completion", fake_completion)

    registry = CollectorRegistry()
    monkeypatch.setattr(curriculum_engine, "lessons_started", Counter("lessons_started", "", registry=registry))
    monkeypatch.setattr(curriculum_engine, "lessons_completed", Counter("lessons_completed", "", registry=registry))
    monkeypatch.setattr(curriculum_engine, "quiz_avg_score", Counter("quiz_avg_score", "", registry=registry))

    with caplog.at_level(logging.INFO):
        await start_lesson(1, slug)
        for q in questions:
            await check_answer(1, lesson_id, q.correct_option)

    assert any("Lesson started" in r.message for r in caplog.records)
    assert any("Lesson completed" in r.message for r in caplog.records)
    assert curriculum_engine.lessons_started._value.get() == 1
    assert curriculum_engine.lessons_completed._value.get() == 1
    assert curriculum_engine.quiz_avg_score._value.get() == 100
