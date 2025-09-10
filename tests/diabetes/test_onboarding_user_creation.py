from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app.diabetes.services import db
import services.api.app.diabetes.handlers.onboarding_handlers as onboarding
import services.api.app.services.onboarding_state as onboarding_state
import services.api.app.diabetes.services.users as users_service


def setup_db() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection: Any, connection_record: Any) -> None:  # pragma: no cover - setup
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)
    return SessionLocal


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(self, text: str, **_: Any) -> None:  # noqa: ANN401
        self.replies.append(text)

    async def reply_video(self, video: Any, **_: Any) -> None:  # noqa: ANN401
        self.replies.append(str(video))


@pytest.mark.asyncio
async def test_start_creates_user(monkeypatch: pytest.MonkeyPatch) -> None:
    SessionLocal = setup_db()
    monkeypatch.setattr(onboarding, "SessionLocal", SessionLocal)
    monkeypatch.setattr(onboarding_state, "SessionLocal", SessionLocal)
    monkeypatch.setattr(users_service, "SessionLocal", SessionLocal)
    monkeypatch.setattr(onboarding, "choose_variant", lambda uid: "A")
    monkeypatch.setattr(onboarding.config, "ONBOARDING_VIDEO_URL", "")

    message = DummyMessage()
    user = SimpleNamespace(id=42)
    update = cast(Update, SimpleNamespace(message=message, effective_user=user))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"tg_init_data": "t"}, job_queue=None, args=[]),
    )

    await onboarding.start_command(update, context)

    with SessionLocal() as session:
        assert session.get(db.User, 42) is not None
        assert session.get(onboarding_state.OnboardingState, 42) is not None
