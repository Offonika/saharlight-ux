from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.services import db
from services.api.app.diabetes.models_learning import (
    Lesson,
    LessonStep,
    QuizQuestion,
    LessonProgress,
)


def setup_db() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)
    return SessionLocal


def test_lesson_crud() -> None:
    SessionLocal = setup_db()
    with SessionLocal() as session:
        lesson = Lesson(
            slug="intro",
            title="Intro",
            content="Basics",
            steps=[
                LessonStep(step_order=1, content="s1"),
                LessonStep(step_order=2, content="s2"),
            ],
        )
        session.add(lesson)
        session.commit()
        session.refresh(lesson)

        stored = session.get(Lesson, lesson.id)
        assert stored is not None
        assert stored.title == "Intro"
        assert stored.is_active is True
        assert [s.content for s in stored.steps] == ["s1", "s2"]


def test_quiz_question_crud() -> None:
    SessionLocal = setup_db()
    with SessionLocal() as session:
        lesson = Lesson(slug="intro", title="Intro", content="Basics")
        session.add(lesson)
        session.commit()
        session.refresh(lesson)

        question = QuizQuestion(
            lesson_id=lesson.id,
            question="2+2?",
            options=["3", "4"],
            correct_option=1,
        )
        session.add(question)
        session.commit()
        session.refresh(question)

        stored = session.get(QuizQuestion, question.id)
        assert stored is not None
        assert stored.lesson_id == lesson.id
        assert stored.options[1] == "4"


def test_lesson_progress_crud() -> None:
    SessionLocal = setup_db()
    with SessionLocal() as session:
        user = db.User(telegram_id=1, thread_id="t1")
        lesson = Lesson(slug="intro", title="Intro", content="Basics")
        session.add_all([user, lesson])
        session.commit()

        progress = LessonProgress(
            user_id=user.telegram_id,
            lesson_id=lesson.id,
            completed=True,
            current_step=0,
            current_question=0,
            quiz_score=80,
        )
        session.add(progress)
        session.commit()
        session.refresh(progress)

        stored = session.get(LessonProgress, progress.id)
        assert stored is not None
        assert stored.completed is True
        assert stored.quiz_score == 80
