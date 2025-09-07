from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.assistant.repositories import memory
from services.api.app.diabetes.services import db


@pytest.fixture()
def session_local() -> sessionmaker[Session]:
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
    return session_local


def test_get_and_upsert(session_local: sessionmaker[Session]) -> None:
    with session_local() as session:
        session.add(db.User(telegram_id=1, thread_id=""))
        session.commit()
        assert memory.get_memory(session, 1) is None

        now = datetime.now(tz=timezone.utc)
        mem = memory.upsert_memory(session, user_id=1, turn_count=1, last_turn_at=now)
        assert mem.turn_count == 1
        assert mem.last_turn_at.replace(tzinfo=timezone.utc) == now

        mem2 = memory.upsert_memory(session, user_id=1, turn_count=2, last_turn_at=now)
        assert mem2.turn_count == 2

        fetched = memory.get_memory(session, 1)
        assert fetched is not None
        assert fetched.turn_count == 2
        assert fetched.last_turn_at.replace(tzinfo=timezone.utc) == now
