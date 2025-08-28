import os
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from services.api.app.diabetes.services.db import Base, User


class DummyMessage:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.polls: list[tuple[str, list[str]]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)

    async def reply_poll(self, question: str, options: list[str], **kwargs: Any) -> Any:
        self.polls.append((question, options))
        return SimpleNamespace(poll=SimpleNamespace(id="p1"))


class DummyQuery:
    def __init__(self, message: DummyMessage, data: str) -> None:
        self.message = message
        self.data = data

    async def answer(self) -> None:  # pragma: no cover - simple stub
        pass


@pytest.mark.asyncio
async def test_start_command_launches_onboarding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "x")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "y")
    import services.api.app.diabetes.handlers.onboarding_handlers as onboarding
    import services.api.app.diabetes.services.gpt_client as gpt_client

    async def fake_thread() -> str:
        return "tid"

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    monkeypatch.setattr(gpt_client, "create_thread", fake_thread)
    monkeypatch.setattr(onboarding, "SessionLocal", TestSession)
    monkeypatch.setattr(onboarding, "commit", lambda s: None)

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
    assert any("1/3" in text for text in message.texts)
    assert context.user_data == {}


@pytest.mark.asyncio
async def test_onboarding_skip_cancels(monkeypatch: pytest.MonkeyPatch) -> None:
    import services.api.app.diabetes.handlers.onboarding_handlers as onboarding

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with TestSession() as session:
        session.add(User(telegram_id=2, thread_id="t"))
        session.commit()

    monkeypatch.setattr(onboarding, "SessionLocal", TestSession)
    monkeypatch.setattr(onboarding, "commit", lambda s: None)
    monkeypatch.setattr(onboarding, "menu_keyboard", lambda: "MK")

    message = DummyMessage()
    query = DummyQuery(message, "onb_skip")
    update = cast(
        Update,
        SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=2)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, bot_data={}),
    )

    state = await onboarding.onboarding_skip(update, context)
    assert state == ConversationHandler.END
    assert context.user_data == {}
    assert message.polls  # poll sent


@pytest.mark.asyncio
async def test_onboarding_icr_invalid_input(monkeypatch: pytest.MonkeyPatch) -> None:
    import services.api.app.diabetes.handlers.onboarding_handlers as onboarding

    message = DummyMessage()
    message.text = "abc"  # type: ignore[attr-defined]
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, bot_data={}),
    )

    state = await onboarding.onboarding_icr(update, context)
    assert state == onboarding.ONB_PROFILE_ICR
    assert context.user_data == {}
    assert any("ИКХ" in text for text in message.texts)


@pytest.mark.asyncio
async def test_onboarding_target_commit_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    import services.api.app.diabetes.handlers.onboarding_handlers as onboarding

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(onboarding, "SessionLocal", TestSession)

    def fail_commit(session: object) -> None:
        raise onboarding.CommitError

    monkeypatch.setattr(onboarding, "commit", fail_commit)
    monkeypatch.setattr(onboarding, "build_timezone_webapp_button", lambda: None)

    message = DummyMessage()
    message.text = "5"  # type: ignore[attr-defined]
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=3)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            user_data={"profile_icr": 10.0, "profile_cf": 3.0}, bot_data={}
        ),
    )

    state = await onboarding.onboarding_target(update, context)
    assert state == ConversationHandler.END
    assert any("Не удалось сохранить профиль" in t for t in message.texts)


@pytest.mark.asyncio
async def test_onboarding_timezone_commit_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    import services.api.app.diabetes.handlers.onboarding_handlers as onboarding

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with TestSession() as session:
        session.add(User(telegram_id=4, thread_id="t"))
        session.commit()

    monkeypatch.setattr(onboarding, "SessionLocal", TestSession)

    def fail_commit(session: object) -> None:
        raise onboarding.CommitError

    monkeypatch.setattr(onboarding, "commit", fail_commit)
    monkeypatch.setattr(onboarding, "build_timezone_webapp_button", lambda: None)

    message = DummyMessage()
    message.text = "Europe/Moscow"  # type: ignore[attr-defined]
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=4)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, bot_data={}),
    )

    state = await onboarding.onboarding_timezone(update, context)
    assert state == ConversationHandler.END
    assert any("Не удалось сохранить часовой пояс" in t for t in message.texts)


@pytest.mark.asyncio
async def test_onboarding_target_manual_timezone_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import services.api.app.diabetes.handlers.onboarding_handlers as onboarding

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(onboarding, "SessionLocal", TestSession)
    monkeypatch.setattr(onboarding, "commit", lambda s: None)
    monkeypatch.setenv("PUBLIC_ORIGIN", "")

    message = DummyMessage()
    message.text = "6"  # type: ignore[attr-defined]
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=5)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            user_data={"profile_icr": 10.0, "profile_cf": 3.0}, bot_data={}
        ),
    )

    state = await onboarding.onboarding_target(update, context)
    assert state == onboarding.ONB_PROFILE_TZ
    assert any("вручную" in t.lower() for t in message.texts)


@pytest.mark.asyncio
async def test_onboarding_demo_next_missing_message() -> None:
    import services.api.app.diabetes.handlers.onboarding_handlers as onboarding

    update = cast(Update, SimpleNamespace(callback_query=SimpleNamespace(message=None)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, bot_data={}),
    )

    state = await onboarding.onboarding_demo_next(update, context)
    assert state == ConversationHandler.END
