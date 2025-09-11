from __future__ import annotations

import importlib
from types import SimpleNamespace
from typing import Any, Callable, cast

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import pytest
from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.services.db as db
import services.api.app.services.profile as profile_service

handlers = importlib.import_module(
    "services.api.app.diabetes.handlers.profile.conversation"
)


class DummyMessage:
    def __init__(self, text: str) -> None:
        self.text: str = text
        self.replies: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)


@pytest.mark.asyncio
async def test_timezone_save_creates_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, class_=Session)
    db.Base.metadata.create_all(bind=engine)

    async def run_db_wrapper(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        kwargs["sessionmaker"] = SessionLocal
        return await db.run_db(fn, *args, **kwargs)

    monkeypatch.setattr(handlers, "run_db", run_db_wrapper)
    monkeypatch.setattr(db, "SessionLocal", SessionLocal, raising=False)
    monkeypatch.setattr(profile_service.db, "SessionLocal", SessionLocal, raising=False)

    msg = DummyMessage("Europe/Moscow")
    update = cast(
        Update, SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(job_queue=SimpleNamespace()),
    )

    await handlers.profile_timezone_save(update, context)
    assert msg.replies == ["✅ Профиль создан. Часовой пояс сохранён."]

    settings = await profile_service.get_profile_settings(1)
    assert settings.timezone == "Europe/Moscow"

    with SessionLocal() as session:
        user = session.get(db.User, 1)
        assert user is not None and user.onboarding_complete is False
