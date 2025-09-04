from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.models_learning import (
    Lesson,
    LessonProgress,
    LessonStep,
    QuizQuestion,
)
from services.api.app.diabetes.services import db


@pytest.fixture()
def setup_db() -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.SessionLocal.configure(bind=engine)
    db.Base.metadata.create_all(bind=engine)


def test_models_crud(setup_db: None) -> None:
    with db.SessionLocal() as session:
        user = db.User(telegram_id=1, thread_id="t1")
        session.add(user)
        lesson = Lesson(slug="intro", title="Intro", content="c", is_active=True)
        session.add(lesson)
        session.flush()
        step = LessonStep(lesson_id=lesson.id, step_order=1, content="step1")
        question = QuizQuestion(
            lesson_id=lesson.id,
            question="Q?",
            options=["A", "B"],
            correct_option=0,
        )
        session.add_all([step, question])
        progress = LessonProgress(user_id=1, lesson_id=lesson.id)
        session.add(progress)
        session.commit()

        fetched = session.query(Lesson).filter_by(slug="intro").one()
        assert fetched.steps[0].content == "step1"
        assert fetched.questions[0].correct_option == 0

        progress.current_step = 1
        session.commit()
        assert session.get(LessonProgress, progress.id).current_step == 1

        session.delete(fetched)
        session.commit()
        assert session.query(Lesson).count() == 0
        assert session.query(LessonStep).count() == 0
        assert session.query(QuizQuestion).count() == 0
