from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes import learning_fixtures
from services.api.app.diabetes.models_learning import Lesson, QuizQuestion
from services.api.app.diabetes.services import db


@pytest.mark.asyncio()
async def test_load_lessons_v0() -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.SessionLocal.configure(bind=engine)
    db.Base.metadata.create_all(bind=engine)
    try:
        path = (
            Path(__file__).resolve().parents[2]
            / "services/api/app/diabetes/content/lessons_v0.json"
        )
        await learning_fixtures.load_lessons(path, sessionmaker=db.SessionLocal)
        with db.SessionLocal() as session:
            lessons = session.query(Lesson).all()
            assert len(lessons) == 3
            for lesson in lessons:
                assert lesson.slug
                steps = lesson.content.splitlines()
                assert len(steps) >= 3
                quiz_count = (
                    session.query(QuizQuestion).filter_by(lesson_id=lesson.id).count()
                )
                assert quiz_count >= 3
    finally:
        db.dispose_engine(engine)
        db.SessionLocal.configure(bind=None)
