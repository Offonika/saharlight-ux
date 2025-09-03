from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession, sessionmaker
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.diabetes.handlers import onboarding_handlers
from services.api.app.diabetes.services import db
from services.api.app.diabetes.services.repository import commit
from services.api.app.services import onboarding_state


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)


@pytest.fixture()
def session_local(monkeypatch: pytest.MonkeyPatch) -> sessionmaker[SASession]:
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine, class_=SASession)
    db.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(db, "SessionLocal", SessionLocal, raising=False)
    monkeypatch.setattr(onboarding_handlers, "SessionLocal", SessionLocal, raising=False)
    monkeypatch.setattr(onboarding_state, "SessionLocal", SessionLocal, raising=False)
    yield SessionLocal
    engine.dispose()


@pytest.mark.asyncio
async def test_reset_onboarding_keeps_profile(session_local: sessionmaker[SASession]) -> None:
    with session_local() as session:
        user = db.User(telegram_id=1, thread_id="t", onboarding_complete=True)
        profile = db.Profile(telegram_id=1, icr=1.23)
        session.add_all([user, profile])
        commit(session)
    await onboarding_state.save_state(1, 2, {"foo": "bar"})

    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(
            effective_message=message,
            message=message,
            effective_user=SimpleNamespace(id=1),
        ),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await onboarding_handlers.reset_onboarding(update, context)

    with session_local() as session:
        assert session.get(onboarding_state.OnboardingState, 1) is None
        user = session.get(db.User, 1)
        assert user is not None
        assert user.onboarding_complete is False
        profile = session.get(db.Profile, 1)
        assert profile is not None
        assert profile.icr == 1.23

    assert any("/start" in r for r in message.replies)

