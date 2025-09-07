import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta, timezone

from services.api.app.config import settings
from services.api.app.assistant.repositories import logs
from services.api.app.diabetes.services import db
from services.api.app.diabetes.models_learning import LearningPlan, LessonLog


@pytest.fixture()
def session_local(monkeypatch: pytest.MonkeyPatch) -> sessionmaker[Session]:
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

    session_local = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(logs, "SessionLocal", session_local)
    return session_local


@pytest.mark.asyncio
async def test_skip_when_logging_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """add_lesson_log should no-op when feature flag is disabled."""

    monkeypatch.setattr(settings, "learning_logging_required", False)

    async def fail_run_db(
        *_: object, **__: object
    ) -> None:  # pragma: no cover - sanity
        raise AssertionError("run_db should not be called")

    monkeypatch.setattr(logs, "run_db", fail_run_db)

    await logs.add_lesson_log(1, 1, 0, 1, "assistant", "hi")


@pytest.mark.asyncio
async def test_add_lesson_log_handles_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Errors during logging must not bubble up."""

    monkeypatch.setattr(settings, "learning_logging_required", True)

    async def fail_run_db(*_: object, **__: object) -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(logs, "run_db", fail_run_db)

    await logs.add_lesson_log(1, 1, 0, 1, "assistant", "hi")


@pytest.mark.asyncio
async def test_add_and_cleanup_logs(
    session_local: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Logs are persisted and old ones are cleaned up."""

    monkeypatch.setattr(settings, "learning_logging_required", True)

    with session_local() as session:
        session.add(db.User(telegram_id=1, thread_id="t"))
        plan = LearningPlan(user_id=1, version=1, plan_json={})
        session.add(plan)
        session.commit()
        plan_id = plan.id
        assert plan_id is not None
        old = LessonLog(
            user_id=1,
            plan_id=plan_id,
            module_idx=0,
            step_idx=0,
            role="assistant",
            content="old",
            created_at=datetime.now(timezone.utc) - timedelta(days=15),
        )
        session.add(old)
        session.commit()

    await logs.add_lesson_log(1, plan_id, 0, 1, "assistant", "new")

    deleted = await logs.cleanup_lesson_logs(14)
    assert deleted == 1

    with session_local() as session:
        rows = session.query(LessonLog).all()
        assert len(rows) == 1
        assert rows[0].content == "new"
