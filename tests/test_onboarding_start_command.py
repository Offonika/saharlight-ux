import os
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from openai import OpenAIError

from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from services.api.app.diabetes.services.db import Base, User


class DummyMessage:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.markups: list[Any] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.markups.append(kwargs.get("reply_markup"))


@pytest.mark.asyncio
async def test_start_command_new_user(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "x")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst")

    import services.api.app.diabetes.handlers.onboarding_handlers as onboarding
    import services.api.app.diabetes.services.gpt_client as gpt_client

    async def fake_create_thread() -> str:
        return "tid"

    monkeypatch.setattr(gpt_client, "create_thread", fake_create_thread)

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(onboarding, "SessionLocal", TestSession)

    called = False

    def fake_skip_markup() -> str:
        nonlocal called
        called = True
        return "SKIP"

    monkeypatch.setattr(onboarding, "_skip_markup", fake_skip_markup)

    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(
            message=message, effective_user=SimpleNamespace(id=1, first_name="Ann")
        ),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, bot_data={}),
    )

    state = await onboarding.start_command(update, context)
    assert state == onboarding.ONB_PROFILE_ICR
    assert called is True
    assert message.markups[-1] == "SKIP"

    with TestSession() as session:
        user = session.get(User, 1)
        assert user is not None
        assert user.thread_id == "tid"


@pytest.mark.asyncio
async def test_start_command_thread_error(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "x")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst")

    import services.api.app.diabetes.handlers.onboarding_handlers as onboarding
    import services.api.app.diabetes.services.gpt_client as gpt_client

    async def fake_create_thread() -> str:
        raise OpenAIError("boom")

    monkeypatch.setattr(gpt_client, "create_thread", fake_create_thread)

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(onboarding, "SessionLocal", TestSession)

    def fake_skip_markup() -> str:  # should not be called
        raise AssertionError("_skip_markup called on error")

    monkeypatch.setattr(onboarding, "_skip_markup", fake_skip_markup)

    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(
            message=message, effective_user=SimpleNamespace(id=1, first_name="Ann")
        ),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, bot_data={}),
    )

    state = await onboarding.start_command(update, context)
    assert state == ConversationHandler.END
    assert any("⚠️" in text for text in message.texts)

    with TestSession() as session:
        assert session.get(User, 1) is None


@pytest.mark.asyncio
async def test_start_command_existing_user(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "x")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst")

    import services.api.app.diabetes.handlers.onboarding_handlers as onboarding

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="tid", onboarding_complete=True))
        session.commit()

    monkeypatch.setattr(onboarding, "SessionLocal", TestSession)
    monkeypatch.setattr(onboarding, "menu_keyboard", lambda: "MK")

    def fake_skip_markup() -> str:  # must not be called
        raise AssertionError("_skip_markup should not be used for existing user")

    monkeypatch.setattr(onboarding, "_skip_markup", fake_skip_markup)

    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(
            message=message, effective_user=SimpleNamespace(id=1, first_name="Ann")
        ),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, bot_data={}),
    )

    state = await onboarding.start_command(update, context)
    assert state == ConversationHandler.END
    assert message.markups[-1] == "MK"
    assert any("Выберите" in text for text in message.texts)
