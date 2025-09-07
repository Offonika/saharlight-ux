from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.assistant.repositories import logs
from services.api.app.diabetes.services import db
from services.api.app.diabetes.models_learning import LearningPlan


@pytest.fixture()
def session_local(monkeypatch: pytest.MonkeyPatch) -> tuple[sessionmaker[Session], int]:
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

    with session_local() as session:
        session.add(db.User(telegram_id=1, thread_id="t"))
        plan = LearningPlan(user_id=1, version=1, plan_json={})
        session.add(plan)
        session.commit()
        plan_id = plan.id

    assert plan_id is not None
    return session_local, plan_id


@pytest.mark.asyncio
async def test_add_and_get_logs(
    session_local: tuple[sessionmaker[Session], int],
) -> None:
    _, plan_id = session_local

    await logs.add_lesson_log(1, plan_id, 0, 1, "assistant", "hi")
    await logs.add_lesson_log(1, plan_id, 0, 1, "user", "answer")

    logs_list = await logs.get_lesson_logs(1, plan_id)
    assert [log.role for log in logs_list] == ["assistant", "user"]
    assert logs_list[0].content == "hi"
    assert logs_list[1].content == "answer"
    assert isinstance(logs_list[0].created_at, type(logs_list[1].created_at))
