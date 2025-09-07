from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.assistant.services import memory_service
from services.api.app.diabetes import commands


@pytest.fixture()
def setup_db(monkeypatch: pytest.MonkeyPatch) -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, class_=Session)
    memory_service.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(memory_service, "SessionLocal", SessionLocal)
    return SessionLocal


@pytest.mark.asyncio
async def test_save_and_get_memory(setup_db: sessionmaker[Session]) -> None:
    await memory_service.save_memory(1, "hello")
    assert await memory_service.get_memory(1) == "hello"


@pytest.mark.asyncio
async def test_clear_memory(setup_db: sessionmaker[Session]) -> None:
    await memory_service.save_memory(1, "hello")
    await memory_service.clear_memory(1)
    assert await memory_service.get_memory(1) is None


@pytest.mark.asyncio
async def test_reset_command_clears_memory(setup_db: sessionmaker[Session]) -> None:
    await memory_service.save_memory(1, "hello")

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
