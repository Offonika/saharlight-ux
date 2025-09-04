from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.learning_fixtures import load_lessons
from services.api.app.diabetes.models_learning import Lesson, QuizQuestion
from services.api.app.diabetes.services import db


def setup_db() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)
    return SessionLocal


@pytest.mark.asyncio()
async def test_load_lessons(tmp_path: Path) -> None:
    sample = [
        {
            "title": "Sample",
            "steps": ["a", "b", "c"],
            "quiz": [
                {"question": "q1", "options": ["1", "2", "3"], "answer": 1},
                {"question": "q2", "options": ["1", "2", "3"], "answer": 2},
                {"question": "q3", "options": ["1", "2", "3"], "answer": 0},
            ],
        }
    ]
    path = tmp_path / "lessons.json"
    path.write_text(json.dumps(sample), encoding="utf-8")

    SessionLocal = setup_db()
    await load_lessons(path, sessionmaker=SessionLocal)

    with SessionLocal() as session:
        lessons = session.query(Lesson).all()
        assert len(lessons) == 1
        assert lessons[0].is_active is True
        questions = session.query(QuizQuestion).filter_by(lesson_id=lessons[0].id).all()
        assert len(questions) == 3
