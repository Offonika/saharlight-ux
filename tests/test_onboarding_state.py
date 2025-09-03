from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession, sessionmaker

import services.api.app.diabetes.services.db as db
import services.api.app.diabetes.onboarding_state as onb_handlers
from services.api.app.diabetes.onboarding_state import (
    OnboardingStateStore,
    reset_onboarding,
)
from services.api.app.services import onboarding_state as onboarding_service
from tests.utils.warn_ctx import warn_or_not


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)


@pytest.mark.asyncio
async def test_reset_command(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    db.Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, class_=SASession)
    monkeypatch.setattr(db, "SessionLocal", SessionLocal, raising=False)
    monkeypatch.setattr(onboarding_service, "SessionLocal", SessionLocal, raising=False)
    monkeypatch.setattr(onb_handlers, "SessionLocal", SessionLocal, raising=False)
    with SessionLocal() as session:
        session.add(db.User(telegram_id=1, thread_id="t", onboarding_complete=True))
        session.add(db.Profile(telegram_id=1, icr=1.23))
        session.add(
            onboarding_service.OnboardingState(user_id=1, step=2, data={}, variant=None)
        )
        session.commit()

    store = OnboardingStateStore()
    store.set_step(1, 2)
    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(
            message=message,
            effective_user=SimpleNamespace(id=1),
            effective_message=message,
        ),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(application=SimpleNamespace(bot_data={"onb_state": store})),
    )
    with warn_or_not(None):
        await reset_onboarding(update, context)
    assert store.get(1).step == 0
    with SessionLocal() as session:
        assert session.get(onboarding_service.OnboardingState, 1) is None
        user = session.get(db.User, 1)
        assert user is not None and user.onboarding_complete is False
        profile = session.get(db.Profile, 1)
        assert profile is not None and profile.icr == 1.23
    assert message.replies and "start" in message.replies[-1].lower()
    engine.dispose()


def test_continue_after_restart() -> None:
    store = OnboardingStateStore()
    store.set_step(1, 2)
    data = store.to_dict()
    with warn_or_not(None):
        restored = OnboardingStateStore.from_dict(data)
    assert restored.get(1).step == 2


def test_auto_reset_after_inactivity() -> None:
    store = OnboardingStateStore()
    state = store.get(1)
    state.step = 2
    state.updated_at = datetime.now(UTC) - timedelta(days=15)
    with warn_or_not(None):
        new_state = store.get(1)
    assert new_state.step == 0
