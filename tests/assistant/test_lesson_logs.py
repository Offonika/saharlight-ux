import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.assistant.repositories import logs
from services.api.app.assistant.repositories.logs import (
    add_lesson_log,
    cleanup_old_logs,
    flush_pending_logs,
)
from services.api.app.assistant.models import LessonLog
from services.api.app.config import settings
from services.api.app.diabetes.services import db
from services.api.app.diabetes.models_learning import LearningPlan


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
    monkeypatch.setattr(logs, "SessionLocal", SessionLocal, raising=False)
    return SessionLocal


@pytest.mark.asyncio
async def test_add_and_flush_logs(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "learning_logging_required", False)

    with session_factory() as session:
        session.add(db.User(telegram_id=1, thread_id="t"))
        session.add(
            LearningPlan(id=1, user_id=1, plan_json=[], is_active=True, version=1)
        )
        session.commit()

    logs.pending_logs.clear()

    async def fail_run_db(*args: object, **kwargs: object) -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(logs, "run_db", fail_run_db)

    await add_lesson_log(1, 1, 0, 1, "assistant", "a")
    await add_lesson_log(1, 1, 0, 2, "user", "b")

    assert len(logs.pending_logs) == 2

    monkeypatch.setattr(logs, "run_db", db.run_db)
    await flush_pending_logs()

    with session_factory() as session:
        entries = session.query(LessonLog).order_by(LessonLog.step_idx).all()
        assert [e.content for e in entries] == ["a", "b"]

    assert not logs.pending_logs


@pytest.mark.asyncio
async def test_cleanup_old_logs(session_factory: sessionmaker[Session]) -> None:
    now = datetime.now(timezone.utc)
    with session_factory() as session:
        session.add(db.User(telegram_id=1, thread_id="t"))
        session.add(
            LearningPlan(id=1, user_id=1, plan_json=[], is_active=True, version=1)
        )
        session.flush()
        session.add(
            LessonLog(
                user_id=1,
                plan_id=1,
                module_idx=0,
                step_idx=0,
                role="assistant",
                content="old",
                created_at=now - timedelta(days=2),
            )
        )
        session.add(
            LessonLog(
                user_id=1,
                plan_id=1,
                module_idx=0,
                step_idx=1,
                role="assistant",
                content="new",
                created_at=now,
            )
        )
        session.commit()

    await cleanup_old_logs(ttl=timedelta(days=1))

    with session_factory() as session:
        contents = [
            log.content for log in session.query(LessonLog).order_by(LessonLog.id)
        ]
        assert contents == ["new"]
