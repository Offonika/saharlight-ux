from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.assistant.repositories import plans as plans_repo
from services.api.app.assistant.repositories import progress as progress_repo
from services.api.app.diabetes.services import db
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
    monkeypatch.setattr(plans_repo, "SessionLocal", session_local, raising=False)
    monkeypatch.setattr(progress_repo, "SessionLocal", session_local, raising=False)
    yield session_local
    db.dispose_engine(engine)


@pytest.mark.asyncio
async def test_restart_restores_step(
    monkeypatch: pytest.MonkeyPatch, setup_db: sessionmaker[Session]
) -> None:
    """Ensure progress survives service restart and plan continues from step 2."""

    with setup_db() as session:  # type: ignore[misc]
        session.add(db.User(telegram_id=1, thread_id=""))
        session.commit()
    plan_id = await plans_repo.create_plan(1, version=1, plan_json=["Шаг 1", "Шаг 2"])
    await progress_repo.upsert_progress(
        1,
        plan_id,
        {"topic": "intro", "module_idx": 0, "step_idx": 2, "snapshot": "Шаг 2"},
    )

    update = SimpleNamespace(
        message=DummyMessage(), effective_user=SimpleNamespace(id=1)
    )
    context = SimpleNamespace(user_data={}, bot_data={})
    monkeypatch.setattr(learning_handlers, "build_main_keyboard", lambda: None)
    monkeypatch.setattr(learning_handlers.settings, "learning_mode_enabled", True)
    monkeypatch.setattr(learning_handlers.settings, "learning_content_mode", "dynamic")

    await learning_handlers.plan_command(update, context)

    assert context.user_data.get("learning_plan_index") == 1
    assert update.message.sent
    assert "Шаг 2" in update.message.sent[0]
