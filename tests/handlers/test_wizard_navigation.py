import os
from types import SimpleNamespace
from typing import Any, Callable, cast

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from services.api.app.diabetes.services.db import Base, User
import services.api.app.services.onboarding_state as onboarding_state
import services.api.app.diabetes.handlers.onboarding_handlers as onboarding
import services.bot.main as main


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.texts: list[str] = []
        self.videos: list[Any] = []
        self.polls: list[tuple[str, list[str]]] = []
        self.reply_markups: list[Any] = []
        self.deleted = False
        self.bot = SimpleNamespace(set_my_commands=AsyncMock())

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.reply_markups.append(kwargs.get("reply_markup"))

    async def reply_video(self, video: Any, **kwargs: Any) -> None:
        self.videos.append(video)

    async def reply_poll(self, question: str, options: list[str], **kwargs: Any) -> Any:
        self.polls.append((question, options))
        return SimpleNamespace(poll=SimpleNamespace(id="p1"))

    async def delete(self) -> None:  # pragma: no cover - interface completeness
        self.deleted = True

    def get_bot(self) -> Any:
        return self.bot


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
    monkeypatch.setattr(onboarding, "choose_variant", lambda uid: "A")


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

    import services.api.app.diabetes.services.users as users_service

    monkeypatch.setattr(gpt_client, "create_thread", fake_thread)
    monkeypatch.setattr(onboarding, "SessionLocal", TestSession)
    monkeypatch.setattr(onboarding, "commit", lambda s: None)

    async def run_db(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        sessionmaker = kwargs.pop("sessionmaker", TestSession)
        with sessionmaker() as session:
            return fn(session, *args, **kwargs)

    monkeypatch.setattr(onboarding, "run_db", run_db)
    monkeypatch.setattr(users_service, "SessionLocal", TestSession)
    monkeypatch.setattr(users_service, "run_db", run_db)

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
    engine.dispose()


@pytest.mark.asyncio
async def test_variant_b_starts_with_timezone(
    monkeypatch: pytest.MonkeyPatch, patch_state: None
) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "x")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "y")
    import services.api.app.diabetes.handlers.onboarding_handlers as onboarding
    import services.api.app.diabetes.services.gpt_client as gpt_client
    import services.api.app.diabetes.services.users as users_service

    monkeypatch.setattr(onboarding, "choose_variant", lambda uid: "B")

    async def fake_thread() -> str:
        return "tid"

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    monkeypatch.setattr(gpt_client, "create_thread", fake_thread)
    monkeypatch.setattr(onboarding, "SessionLocal", TestSession)
    monkeypatch.setattr(onboarding, "commit", lambda s: None)

    async def run_db(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        sessionmaker = kwargs.pop("sessionmaker", TestSession)
        with sessionmaker() as session:
            return fn(session, *args, **kwargs)

    monkeypatch.setattr(onboarding, "run_db", run_db)
    monkeypatch.setattr(users_service, "SessionLocal", TestSession)
    monkeypatch.setattr(users_service, "run_db", run_db)

    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=5)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, bot_data={}),
    )

    state = await onboarding.start_command(update, context)
    assert state == onboarding.TIMEZONE
    assert any("1/3" in text for text in message.texts)
    engine.dispose()


@pytest.mark.asyncio
async def test_profile_back_returns_menu(monkeypatch: pytest.MonkeyPatch) -> None:
    import services.api.app.diabetes.handlers.profile as profile

    monkeypatch.setattr(profile, "build_main_keyboard", lambda: "MK")
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
    import services.api.app.diabetes.services.users as users_service

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with TestSession() as session:
        session.add(User(telegram_id=2, thread_id="t"))
        session.commit()

    monkeypatch.setattr(onboarding, "SessionLocal", TestSession)
    monkeypatch.setattr(onboarding, "commit", lambda s: None)
    monkeypatch.setattr(onboarding, "build_main_keyboard", lambda: "MK")
    async def run_db(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        sessionmaker = kwargs.pop("sessionmaker", TestSession)
        with sessionmaker() as session:
            return fn(session, *args, **kwargs)

    monkeypatch.setattr(onboarding, "run_db", run_db)
    monkeypatch.setattr(users_service, "SessionLocal", TestSession)
    monkeypatch.setattr(users_service, "run_db", run_db)

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
    assert not message.polls
    assert message.texts[0] == "Пропущено"
    assert message.reply_markups[0] == "MK"
    assert any("/learn" in t for t in message.texts[1:])
    message.bot.set_my_commands.assert_awaited_once_with(main.commands)
    engine.dispose()


@pytest.mark.asyncio
async def test_profile_cancel_outputs_text(monkeypatch: pytest.MonkeyPatch) -> None:
    import services.api.app.diabetes.handlers.profile as profile

    monkeypatch.setattr(profile, "build_main_keyboard", lambda: "MK")
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
    import services.api.app.diabetes.services.users as users_service

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with TestSession() as session:
        session.add(User(telegram_id=3, thread_id="t"))
        session.commit()

    monkeypatch.setattr(onboarding, "SessionLocal", TestSession)
    monkeypatch.setattr(onboarding, "commit", lambda s: None)
    monkeypatch.setattr(onboarding, "build_main_keyboard", lambda: "MK")
    async def run_db(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        sessionmaker = kwargs.pop("sessionmaker", TestSession)
        with sessionmaker() as session:
            return fn(session, *args, **kwargs)

    monkeypatch.setattr(onboarding, "run_db", run_db)
    monkeypatch.setattr(users_service, "SessionLocal", TestSession)
    monkeypatch.setattr(users_service, "run_db", run_db)

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
    engine.dispose()
