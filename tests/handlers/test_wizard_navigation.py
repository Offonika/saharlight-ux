import os
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from services.api.app.diabetes.services.db import Base, User
import services.api.app.services.onboarding_state as onboarding_state
import services.api.app.diabetes.handlers.onboarding_handlers as onboarding


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.texts: list[str] = []
        self.polls: list[tuple[str, list[str]]] = []
        self.deleted = False

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)

    async def reply_poll(self, question: str, options: list[str], **kwargs: Any) -> Any:
        self.polls.append((question, options))
        return SimpleNamespace(poll=SimpleNamespace(id="p1"))

    async def delete(self) -> None:  # pragma: no cover - interface completeness
        self.deleted = True


class DummyQuery:
    def __init__(self, message: DummyMessage, data: str) -> None:
        self.message = message
        self.data = data
        self.answered = False

    async def answer(self) -> None:
        self.answered = True


@pytest.fixture()
def patch_state(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_save_state(*args: Any, **kwargs: Any) -> None:  # pragma: no cover - no logic
        pass

    async def fake_load_state(*args: Any, **kwargs: Any) -> Any:
        return None

    async def fake_complete_state(*args: Any, **kwargs: Any) -> None:  # pragma: no cover - no logic
        pass

    monkeypatch.setattr(onboarding_state, "save_state", fake_save_state)
    monkeypatch.setattr(onboarding_state, "load_state", fake_load_state)
    monkeypatch.setattr(onboarding_state, "complete_state", fake_complete_state)
    async def noop_mark(user_id: int) -> None:  # pragma: no cover - no logic
        pass

    monkeypatch.setattr(onboarding, "_mark_user_complete", noop_mark)


@pytest.mark.asyncio
async def test_start_triggers_onboarding(
    monkeypatch: pytest.MonkeyPatch, patch_state: None
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
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1, first_name="Ann")),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, bot_data={}),
    )

    state = await onboarding.start_command(update, context)
    assert state == onboarding.ONB_PROFILE_ICR
    assert any("1/3" in text for text in message.texts)


@pytest.mark.asyncio
async def test_profile_back_returns_menu(monkeypatch: pytest.MonkeyPatch) -> None:
    import services.api.app.diabetes.handlers.profile as profile

    monkeypatch.setattr(profile, "menu_keyboard", lambda: "MK")
    message = DummyMessage()
    query = DummyQuery(message, "profile_back")
    update = cast(Update, SimpleNamespace(callback_query=query))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await profile.profile_back(update, context)
    assert message.deleted
    assert message.texts == ["📋 Выберите действие:"]


@pytest.mark.asyncio
async def test_onboarding_skip_sends_final(
    monkeypatch: pytest.MonkeyPatch, patch_state: None
) -> None:
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
    assert message.polls
    assert any("Пропущено" in text for text in message.texts)


@pytest.mark.asyncio
async def test_profile_cancel_outputs_text(monkeypatch: pytest.MonkeyPatch) -> None:
    import services.api.app.diabetes.handlers.profile as profile

    monkeypatch.setattr(profile, "menu_keyboard", lambda: "MK")
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    state = await profile.profile_cancel(update, context)
    assert state == profile.END
    assert message.texts == ["Отменено."]


@pytest.mark.asyncio
async def test_onboarding_completion_message(
    monkeypatch: pytest.MonkeyPatch, patch_state: None
) -> None:
    import services.api.app.diabetes.handlers.onboarding_handlers as onboarding

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with TestSession() as session:
        session.add(User(telegram_id=3, thread_id="t"))
        session.commit()

    monkeypatch.setattr(onboarding, "SessionLocal", TestSession)
    monkeypatch.setattr(onboarding, "commit", lambda s: None)
    monkeypatch.setattr(onboarding, "menu_keyboard", lambda: "MK")

    message = DummyMessage()
    query = DummyQuery(message, "onb_rem_no")
    update = cast(
        Update,
        SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=3)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot_data={}, job_queue=None),
    )

    state = await onboarding.onboarding_reminders(update, context)
    assert state == ConversationHandler.END
    assert any("Готово" in text for text in message.texts)
