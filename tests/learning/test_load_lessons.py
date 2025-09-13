from __future__ import annotations

from unittest.mock import patch

import logging
import pytest
from typing import Callable
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session

from services.api.app.diabetes import learning_fixtures
from services.api.app.diabetes.models_learning import Lesson, QuizQuestion
from services.api.app.diabetes.prompts import LESSONS_V0_PATH
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
        path = LESSONS_V0_PATH
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
async def test_main_loads_lessons(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    def fake_init_db() -> None:
        db.SessionLocal.configure(bind=engine)
        db.Base.metadata.create_all(bind=engine)

    async def fake_run_db(
        fn: Callable[[Session, object], object], *args: object, sessionmaker=None, **kwargs: object
    ) -> object:
        sm = sessionmaker or db.SessionLocal
        with engine.begin() as connection:
            with sm(bind=connection) as session:
                return fn(session, *args, **kwargs)

    path = LESSONS_V0_PATH
    monkeypatch.setattr(learning_fixtures, "run_db", fake_run_db)
    with patch(
        "services.api.app.diabetes.learning_fixtures.init_db", side_effect=fake_init_db
    ) as init_db_mock, caplog.at_level(logging.INFO):
        await learning_fixtures.main([str(path)])
        init_db_mock.assert_called_once()
        with db.SessionLocal() as session:
            lessons = session.query(Lesson).all()
            assert len(lessons) > 0
    assert "OK: lessons loaded" in caplog.text

    db.dispose_engine(engine)
    db.SessionLocal.configure(bind=None)
