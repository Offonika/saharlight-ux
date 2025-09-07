from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.assistant.services import memory_service
from services.api.app.diabetes import assistant_state
from services.api.app.diabetes.services import db


@pytest.fixture()
def setup_db(monkeypatch: pytest.MonkeyPatch) -> sessionmaker[Session]:
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
    monkeypatch.setattr(memory_service, "SessionLocal", SessionLocal)
    with SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id=""))
        session.commit()
    return SessionLocal


@pytest.mark.asyncio
async def test_summary_persisted(
    monkeypatch: pytest.MonkeyPatch, setup_db: sessionmaker[Session]
) -> None:
    monkeypatch.setattr(assistant_state, "ASSISTANT_MAX_TURNS", 2)
    monkeypatch.setattr(assistant_state, "ASSISTANT_SUMMARY_TRIGGER", 3)

    def fake_summary(parts: list[str]) -> str:
        return ",".join(parts)

    monkeypatch.setattr(assistant_state, "summarize", fake_summary)

    user_data: dict[str, object] = {}
    base = datetime.now(tz=timezone.utc)
    for i in range(3):
        await memory_service.record_turn(
            1, user_data, f"a{i}", now=base + timedelta(minutes=i)
        )

    mem = await memory_service.get_memory(1)
    assert mem is not None
    assert mem.summary_text == "a0"
    assert mem.turn_count == 1
    last = mem.last_turn_at.replace(tzinfo=timezone.utc)
    assert abs(last - (base + timedelta(minutes=2))) < timedelta(seconds=1)
    assert user_data[assistant_state.HISTORY_KEY] == ["a1", "a2"]
