from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.onboarding_handlers as onboarding
from services.api.app.diabetes.services import db


class DummyMessage:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_reset_onboarding_clears_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        user = db.User(telegram_id=1, thread_id="t", onboarding_complete=True)
        profile = db.Profile(telegram_id=1, timezone="UTC")
        state = db.OnboardingState(telegram_id=1)
        session.add_all([user, profile, state])
        session.commit()

    monkeypatch.setattr(onboarding, "SessionLocal", SessionLocal)

    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await onboarding.reset_onboarding(update, context)

    assert message.texts

    with SessionLocal() as session:
        assert session.get(db.OnboardingState, 1) is None
        user = session.get(db.User, 1)
        assert user is not None and user.onboarding_complete is False
        profile = session.get(db.Profile, 1)
        assert profile is not None and profile.timezone == "UTC"
