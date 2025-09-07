from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.services import db
from services.api.app.assistant.services import progress_service
from services.api.app.diabetes import learning_handlers


class DummyMessage:
    """Capture replies for assertions."""

    def __init__(self) -> None:
        self.sent: list[str] = []

    async def reply_text(
        self, text: str, **_kwargs: Any
    ) -> None:  # pragma: no cover - simple capture
        self.sent.append(text)


@pytest.fixture()
def setup_db(monkeypatch: pytest.MonkeyPatch) -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(db, "SessionLocal", session_local, raising=False)
    monkeypatch.setattr(progress_service, "SessionLocal", session_local, raising=False)
    yield session_local
    db.dispose_engine(engine)


@pytest.mark.asyncio
async def test_restart_restores_step(
    monkeypatch: pytest.MonkeyPatch, setup_db: sessionmaker[Session]
) -> None:
    """Ensure progress survives service restart and plan continues from step 2."""

    await progress_service.upsert_progress(1, "intro", 2)
    progress = await progress_service.get_progress(1, "intro")
    assert progress is not None

    bot_data = {
        learning_handlers.PROGRESS_KEY: {
            1: {"topic": progress.lesson, "module_idx": 0, "step_idx": progress.step}
        }
    }
    update = SimpleNamespace(
        message=DummyMessage(), effective_user=SimpleNamespace(id=1)
    )
    context = SimpleNamespace(user_data={}, bot_data=bot_data)

    async def fake_generate_step_text(*args: object, **kwargs: object) -> str:
        return "Шаг 2"

    monkeypatch.setattr(
        learning_handlers, "generate_step_text", fake_generate_step_text
    )
    monkeypatch.setattr(learning_handlers, "build_main_keyboard", lambda: None)

    await learning_handlers.plan_command(update, context)

    assert context.user_data.get("learning_plan_index") == 1
    assert update.message.sent
    assert "Шаг 2" in update.message.sent[0]
