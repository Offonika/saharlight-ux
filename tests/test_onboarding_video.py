from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any, Callable, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram import Update
import telegram.error
from telegram.ext import CallbackContext, ConversationHandler

import services.api.app.diabetes.handlers.onboarding_handlers as onboarding
import services.api.app.diabetes.services.users as users_service
import services.api.app.diabetes.services.db as db


@pytest.fixture(autouse=True)
def fake_db(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    db.Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    async def run_db(
        fn: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:  # pragma: no cover - simple sync stub
        session_maker = kwargs.pop("sessionmaker", TestSession)
        with session_maker() as session:
            return fn(session, *args, **kwargs)

    monkeypatch.setattr(onboarding, "SessionLocal", TestSession, raising=False)
    monkeypatch.setattr(users_service, "SessionLocal", TestSession, raising=False)
    monkeypatch.setattr(onboarding, "run_db", run_db, raising=False)
    monkeypatch.setattr(users_service, "run_db", run_db, raising=False)


class DummyMessage:
    def __init__(self) -> None:
        self.videos: list[str] = []
        self.texts: list[str] = []

    async def reply_video(self, url: str, **kwargs: Any) -> None:
        self.videos.append(url)

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)


async def _noop_prompt(*args: Any, **kwargs: Any) -> int:
    return ConversationHandler.END


@pytest.mark.asyncio
async def test_start_command_sends_video(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        onboarding.config, "ONBOARDING_VIDEO_URL", "https://e.co/v.mp4", raising=False
    )

    async def _load_state(uid: int) -> None:
        return None

    monkeypatch.setattr(onboarding.onboarding_state, "load_state", _load_state)
    monkeypatch.setattr(onboarding, "_prompt_profile", _noop_prompt)
    monkeypatch.setattr(onboarding, "_prompt_timezone", _noop_prompt)
    monkeypatch.setattr(onboarding, "_prompt_reminders", _noop_prompt)

    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"tg_init_data": "t"}, job_queue=None),
    )

    await onboarding.start_command(update, context)
    assert message.videos == ["https://e.co/v.mp4"]
    assert not message.texts


@pytest.mark.asyncio
async def test_start_command_sends_link_on_failure(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        onboarding.config, "ONBOARDING_VIDEO_URL", "https://e.co/v.mp4", raising=False
    )

    async def _load_state(uid: int) -> None:
        return None

    monkeypatch.setattr(onboarding.onboarding_state, "load_state", _load_state)
    monkeypatch.setattr(onboarding, "_prompt_profile", _noop_prompt)
    monkeypatch.setattr(onboarding, "_prompt_timezone", _noop_prompt)
    monkeypatch.setattr(onboarding, "_prompt_reminders", _noop_prompt)

    message = DummyMessage()

    async def fail_video(
        url: str, **kwargs: Any
    ) -> None:  # pragma: no cover - forced error
        raise telegram.error.TelegramError("boom")

    message.reply_video = fail_video  # type: ignore[assignment]

    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"tg_init_data": "t"}, job_queue=None),
    )

    with caplog.at_level(logging.WARNING):
        await onboarding.start_command(update, context)
    assert message.texts == ["https://e.co/v.mp4"]
    assert not message.videos
    assert "Failed to send onboarding video" in caplog.text
