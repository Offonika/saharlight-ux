from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.assistant.models import LessonLog
from services.api.app.diabetes.models_learning import LearningPlan
from services.api.app.diabetes.services import db


@pytest.fixture()
def session_factory(monkeypatch: pytest.MonkeyPatch) -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection, connection_record) -> None:  # pragma: no cover - setup
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(db, "SessionLocal", SessionLocal, raising=False)
    return SessionLocal


def test_lesson_logs_deleted_with_user(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        user = db.User(telegram_id=1, thread_id="")
        session.add(user)
        session.flush()
        plan = LearningPlan(user_id=1, version=1, plan_json={})
        session.add(plan)
        session.flush()
        session.add(
            LessonLog(
                user_id=1,
                plan_id=plan.id,
                module_idx=0,
                step_idx=0,
                role="assistant",
                content="hi",
            )
        )
        session.commit()

        assert session.query(LessonLog).count() == 1

        session.delete(user)
        session.commit()

        assert session.query(LessonLog).count() == 0
