from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession, sessionmaker
from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.onboarding_handlers as onboarding
from services.api.app.diabetes.services import db
from services.api.app.services import onboarding_state
import services.api.app.services.profile as profile_service


class DummyMessage:
    def __init__(self, data: str) -> None:
        self.web_app_data = SimpleNamespace(data=data)
        self.replies: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)


@pytest.fixture()
def session_local(monkeypatch: pytest.MonkeyPatch) -> sessionmaker[SASession]:
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine, class_=SASession)
    db.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(db, "SessionLocal", SessionLocal, raising=False)
    monkeypatch.setattr(onboarding, "SessionLocal", SessionLocal, raising=False)
    monkeypatch.setattr(onboarding_state, "SessionLocal", SessionLocal, raising=False)
    monkeypatch.setattr(profile_service.db, "SessionLocal", SessionLocal, raising=False)
    yield SessionLocal
    engine.dispose()


@pytest.mark.asyncio
async def test_timezone_webapp_saves(session_local: sessionmaker[SASession]) -> None:
    user_id = 1
    await onboarding_state.save_state(user_id, onboarding.TIMEZONE, {}, None)
    message = DummyMessage("Europe/Moscow")
    update = cast(
        Update,
        SimpleNamespace(
            message=message,
            effective_user=SimpleNamespace(id=user_id),
        ),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    state = await onboarding.timezone_webapp(update, context)
    assert state == onboarding.REMINDERS
    assert context.user_data["timezone"] == "Europe/Moscow"
    with session_local() as session:
        prof = session.get(db.Profile, user_id)
        assert prof is not None
        assert prof.timezone == "Europe/Moscow"
        assert prof.timezone_auto is True
        st = session.get(onboarding_state.OnboardingState, user_id)
        assert st is not None
        assert st.step == onboarding.REMINDERS
        assert st.data.get("timezone") == "Europe/Moscow"
