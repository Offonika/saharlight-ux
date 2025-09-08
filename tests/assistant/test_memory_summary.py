from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.assistant.services import memory_service
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
async def test_record_turn_increments(
    setup_db: sessionmaker[Session],
) -> None:
    base = datetime.now(tz=timezone.utc)
    for i in range(3):
        await memory_service.record_turn(1, now=base + timedelta(minutes=i))

    mem = await memory_service.get_memory(1)
    assert mem is not None
    assert mem.turn_count == 3
    last = mem.last_turn_at.replace(tzinfo=timezone.utc)
    assert abs(last - (base + timedelta(minutes=2))) < timedelta(seconds=1)


@pytest.mark.asyncio
async def test_record_turn_updates_summary(
    setup_db: sessionmaker[Session],
) -> None:
    now = datetime.now(tz=timezone.utc)
    await memory_service.record_turn(1, summary_text="hi", now=now)
    mem = await memory_service.get_memory(1)
    assert mem is not None
    assert mem.summary_text == "hi"
    await memory_service.record_turn(
        1, summary_text="bye", now=now + timedelta(minutes=1)
    )
    mem = await memory_service.get_memory(1)
    assert mem.summary_text == "bye"


@pytest.mark.asyncio
async def test_record_turn_concurrent(
    setup_db: sessionmaker[Session],
) -> None:
    now = datetime.now(tz=timezone.utc)

    async def call(i: int) -> None:
        await memory_service.record_turn(1, now=now + timedelta(minutes=i))

    await asyncio.gather(*(call(i) for i in range(10)))

    mem = await memory_service.get_memory(1)
    assert mem is not None
    assert mem.turn_count == 10
