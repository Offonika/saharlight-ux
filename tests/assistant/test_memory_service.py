from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.assistant.services import memory_service
from services.api.app.diabetes import commands
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
async def test_save_and_get_memory(setup_db: sessionmaker[Session]) -> None:
    now = datetime.now(tz=timezone.utc)
    await memory_service.save_memory(
        1, summary_text="hello", turn_count=1, last_turn_at=now
    )
    mem = await memory_service.get_memory(1)
    assert mem is not None
    assert mem.summary_text == "hello"
    assert mem.turn_count == 1


@pytest.mark.asyncio
async def test_clear_memory(setup_db: sessionmaker[Session]) -> None:
    now = datetime.now(tz=timezone.utc)
    await memory_service.save_memory(
        1, summary_text="hello", turn_count=1, last_turn_at=now
    )
    await memory_service.clear_memory(1)
    assert await memory_service.get_memory(1) is None


@pytest.mark.asyncio
async def test_reset_command_clears_memory(setup_db: sessionmaker[Session]) -> None:
    now = datetime.now(tz=timezone.utc)
    await memory_service.save_memory(
        1, summary_text="hello", turn_count=1, last_turn_at=now
    )

    class DummyMessage:
        def __init__(self) -> None:
            self.sent: list[str] = []

        async def reply_text(self, text: str) -> None:
            self.sent.append(text)

    update = SimpleNamespace(
        effective_message=DummyMessage(),
        effective_user=SimpleNamespace(id=1),
    )
    context = SimpleNamespace(
        user_data={"assistant_history": ["x"], "assistant_summary": "y"}
    )

    await commands.reset_command(update, context)

    assert await memory_service.get_memory(1) is None
    assert context.user_data == {}
