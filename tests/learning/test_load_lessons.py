from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

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
        path = Path(__file__).resolve().parents[2] / "content/lessons_v0.json"
        await learning_fixtures.load_lessons(path, sessionmaker=db.SessionLocal)
        with db.SessionLocal() as session:
            lessons = session.query(Lesson).all()
            assert len(lessons) == 4
            assert any(lesson.slug == "xe_basics" for lesson in lessons)
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


@pytest.mark.asyncio()
async def test_main_loads_lessons() -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    def fake_init_db() -> None:
        db.SessionLocal.configure(bind=engine)
        db.Base.metadata.create_all(bind=engine)

    path = Path(__file__).resolve().parents[2] / "content/lessons_v0.json"
    with patch(
        "services.api.app.diabetes.learning_fixtures.init_db", side_effect=fake_init_db
    ) as init_db_mock:
        await learning_fixtures.main([str(path)])
        init_db_mock.assert_called_once()
        with db.SessionLocal() as session:
            lessons = session.query(Lesson).all()
            assert len(lessons) > 0

    db.dispose_engine(engine)
    db.SessionLocal.configure(bind=None)
