from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes import learning_fixtures
from services.api.app.diabetes.models_learning import Lesson
from services.api.app.diabetes.services import db


def test_load_lessons() -> None:
    path = Path(__file__).with_name("lessons_v0.json")
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.SessionLocal.configure(bind=engine)
    db.Base.metadata.create_all(bind=engine)
    try:
        learning_fixtures.load(path)
        with db.SessionLocal() as session:
            lessons = session.execute(select(Lesson)).scalars().all()
            assert len(lessons) == 3
            for lesson in lessons:
                assert len(lesson.content.splitlines()) >= 3
                assert len(lesson.questions) >= 3
    finally:
        db.dispose_engine(engine)
        db.SessionLocal.configure(bind=None)
