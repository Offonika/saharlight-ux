from types import SimpleNamespace
from typing import Any, Callable, cast
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession, sessionmaker
from sqlalchemy.pool import StaticPool
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

    async def reply_video(self, video: Any, **kwargs: Any) -> None:
        self.replies.append(video)


@pytest.fixture()
def session_local(monkeypatch: pytest.MonkeyPatch) -> sessionmaker[SASession]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, class_=SASession)
    db.Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(db, "SessionLocal", SessionLocal, raising=False)
    monkeypatch.setattr(onboarding, "SessionLocal", SessionLocal, raising=False)
    monkeypatch.setattr(onboarding_state, "SessionLocal", SessionLocal, raising=False)
    monkeypatch.setattr(profile_service.db, "SessionLocal", SessionLocal, raising=False)

    async def run_db(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        sessionmaker = kwargs.get("sessionmaker")
        if sessionmaker is not None:
            return fn(sessionmaker())
        return fn(*args, **kwargs)

    monkeypatch.setattr(db, "run_db", run_db, raising=False)
    monkeypatch.setattr(onboarding_state, "run_db", run_db, raising=False)
    monkeypatch.setattr(profile_service.db, "run_db", run_db, raising=False)
    monkeypatch.setattr(onboarding, "run_db", run_db, raising=False)
    yield SessionLocal
    engine.dispose()


@pytest.mark.asyncio
async def test_timezone_webapp_saves(
    session_local: sessionmaker[SASession], monkeypatch: pytest.MonkeyPatch
) -> None:
    save_mock = AsyncMock()
    monkeypatch.setattr(profile_service, "save_timezone", save_mock, raising=False)
    monkeypatch.setattr(onboarding, "save_timezone", save_mock, raising=False)

    user_id = 1
    await onboarding_state.save_state(user_id, onboarding.TIMEZONE, {}, None)
    message = DummyMessage("Europe/Moscow")
    update = cast(
        Update,
        SimpleNamespace(
            message=message,
            effective_message=message,
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
    save_mock.assert_awaited_once_with(user_id, "Europe/Moscow", auto=True)
    with session_local() as session:
        st = session.get(onboarding_state.OnboardingState, user_id)
        assert st is not None
        assert st.step == onboarding.REMINDERS
        assert st.data.get("timezone") == "Europe/Moscow"


@pytest.mark.asyncio
async def test_timezone_webapp_rejects_invalid(
    session_local: sessionmaker[SASession], monkeypatch: pytest.MonkeyPatch
) -> None:
    save_mock = AsyncMock()
    monkeypatch.setattr(onboarding, "save_timezone", save_mock, raising=False)
    monkeypatch.setattr(profile_service, "save_timezone", save_mock, raising=False)

    user_id = 1
    await onboarding_state.save_state(user_id, onboarding.TIMEZONE, {}, None)
    message = DummyMessage("Invalid/Zone")
    update = cast(
        Update,
        SimpleNamespace(
            message=message,
            effective_message=message,
            effective_user=SimpleNamespace(id=user_id),
        ),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    state = await onboarding.timezone_webapp(update, context)
    assert state == onboarding.TIMEZONE
    assert message.replies == ["Некорректный часовой пояс. Пример: Europe/Moscow"]
    save_mock.assert_not_called()
    assert "timezone" not in context.user_data
    with session_local() as session:
        st = session.get(onboarding_state.OnboardingState, user_id)
        assert st is not None
        assert st.step == onboarding.TIMEZONE
        assert st.data == {}
