import logging
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from services.api.app.diabetes.services.db import Base, User, Reminder


class DummyMessage:
    def __init__(self, poll_obj: Any | None = SimpleNamespace(id="p1")) -> None:
        self.texts: list[str] = []
        self.photos: list[tuple[Any, str | None]] = []
        self.polls: list[tuple[str, list[str]]] = []
        self.markups: list[Any] = []
        self.kwargs: list[dict[str, Any]] = []
        self.poll_obj = poll_obj
        self.text: str | None = None

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.markups.append(kwargs.get("reply_markup"))
        self.kwargs.append(kwargs)

    async def reply_photo(
        self, photo: Any, caption: str | None = None, **kwargs: Any
    ) -> None:
        self.photos.append((photo, caption))
        self.markups.append(kwargs.get("reply_markup"))
        self.kwargs.append(kwargs)

    async def reply_poll(
        self, question: str, options: list[str], **kwargs: Any
    ) -> SimpleNamespace:
        self.polls.append((question, options))
        self.markups.append(kwargs.get("reply_markup"))
        self.kwargs.append(kwargs)
        return SimpleNamespace(poll=self.poll_obj)

    async def delete(self) -> None:
        pass


class DummyQuery:
    def __init__(self, message: DummyMessage, data: str) -> None:
        self.message = message
        self.data = data

    async def answer(self) -> None:
        pass


@pytest.mark.asyncio
async def test_onboarding_profile_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    import services.api.app.diabetes.handlers.onboarding_handlers as onboarding

    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=None, bot_data={}),
    )

    message.text = "abc"
    state = await onboarding.onboarding_icr(update, context)
    assert state == onboarding.ONB_PROFILE_ICR
    assert "Введите ИКХ числом." in message.texts[-1]

    message.text = "0"
    state = await onboarding.onboarding_icr(update, context)
    assert state == onboarding.ONB_PROFILE_ICR
    assert "ИКХ должен быть больше 0." in message.texts[-1]

    message.text = "10"
    state = await onboarding.onboarding_icr(update, context)
    assert state == onboarding.ONB_PROFILE_CF

    message.text = "abc"
    state = await onboarding.onboarding_cf(update, context)
    assert state == onboarding.ONB_PROFILE_CF
    assert "Введите КЧ числом." in message.texts[-1]

    message.text = "-3"
    state = await onboarding.onboarding_cf(update, context)
    assert state == onboarding.ONB_PROFILE_CF
    assert "КЧ должен быть больше 0." in message.texts[-1]

    message.text = "3"
    state = await onboarding.onboarding_cf(update, context)
    assert state == onboarding.ONB_PROFILE_TARGET

    message.text = "abc"
    state = await onboarding.onboarding_target(update, context)
    assert state == onboarding.ONB_PROFILE_TARGET
    assert "Введите целевой сахар числом." in message.texts[-1]

    message.text = "0"
    state = await onboarding.onboarding_target(update, context)
    assert state == onboarding.ONB_PROFILE_TARGET
    assert "Целевой сахар должен быть больше 0." in message.texts[-1]

    context.user_data = {}
    message.text = "5"
    state = await onboarding.onboarding_target(update, context)
    assert state == ConversationHandler.END
    assert any("Не хватает данных" in t for t in message.texts)


@pytest.mark.asyncio
async def test_onboarding_timezone_invalid(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import services.api.app.diabetes.handlers.onboarding_handlers as onboarding

    monkeypatch.setattr(onboarding, "build_timezone_webapp_button", lambda: None)

    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, bot_data={}),
    )

    message.text = "Mars/Phobos"
    with caplog.at_level(logging.WARNING):
        state = await onboarding.onboarding_timezone(update, context)
    assert state == onboarding.ONB_PROFILE_TZ
    assert any("Введите корректный часовой пояс" in t for t in message.texts)
    assert "Invalid timezone provided by user" in caplog.text


@pytest.mark.asyncio
async def test_onboarding_reminders_repeated(monkeypatch: pytest.MonkeyPatch) -> None:
    import services.api.app.diabetes.handlers.onboarding_handlers as onboarding

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(onboarding, "SessionLocal", TestSession)
    monkeypatch.setattr(onboarding, "menu_keyboard", "MK")

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    message = DummyMessage()
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, bot_data={}, job_queue=None),
    )

    query_yes = DummyQuery(message, "onb_rem_yes")
    update_yes = cast(
        Update,
        SimpleNamespace(callback_query=query_yes, effective_user=SimpleNamespace(id=1)),
    )
    state = await onboarding.onboarding_reminders(update_yes, context)
    assert state == ConversationHandler.END

    query_yes2 = DummyQuery(message, "onb_rem_yes")
    update_yes2 = cast(
        Update,
        SimpleNamespace(callback_query=query_yes2, effective_user=SimpleNamespace(id=1)),
    )
    state = await onboarding.onboarding_reminders(update_yes2, context)
    assert state == ConversationHandler.END

    query_no = DummyQuery(message, "onb_rem_no")
    update_no = cast(
        Update,
        SimpleNamespace(callback_query=query_no, effective_user=SimpleNamespace(id=1)),
    )
    state = await onboarding.onboarding_reminders(update_no, context)
    assert state == ConversationHandler.END

    with TestSession() as session:
        reminders = session.query(Reminder).filter_by(telegram_id=1).all()
        assert len(reminders) == 1
        assert reminders[0].is_enabled is False


@pytest.mark.asyncio
async def test_onboarding_reminders_poll_missing(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import services.api.app.diabetes.handlers.onboarding_handlers as onboarding

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(onboarding, "SessionLocal", TestSession)
    monkeypatch.setattr(onboarding, "menu_keyboard", "MK")

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    message = DummyMessage(poll_obj=None)
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, bot_data={}, job_queue=None),
    )

    query_yes = DummyQuery(message, "onb_rem_yes")
    update = cast(
        Update,
        SimpleNamespace(callback_query=query_yes, effective_user=SimpleNamespace(id=1)),
    )
    with caplog.at_level(logging.WARNING):
        state = await onboarding.onboarding_reminders(update, context)
    assert state == ConversationHandler.END
    assert any("Poll message missing poll object" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_onboarding_skip_commit_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    import services.api.app.diabetes.handlers.onboarding_handlers as onboarding

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(onboarding, "SessionLocal", TestSession)
    monkeypatch.setattr(onboarding, "commit", lambda session: False)
    monkeypatch.setattr(onboarding, "menu_keyboard", "MK")

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    message = DummyMessage()
    query = DummyQuery(message, "onb_skip")
    update = cast(
        Update,
        SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}, bot_data={}),
    )

    state = await onboarding.onboarding_skip(update, context)
    assert state == ConversationHandler.END
    assert message.polls == []
    assert any("Не удалось сохранить" in t for t in message.texts)


@pytest.mark.asyncio
async def test_onboarding_poll_answer_logging(caplog: pytest.LogCaptureFixture) -> None:
    import services.api.app.diabetes.handlers.onboarding_handlers as onboarding

    update = cast(
        Update,
        SimpleNamespace(poll_answer=SimpleNamespace(poll_id="p1", option_ids=[2])),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot_data={"onboarding_polls": {"p1": 42}}),
    )

    with caplog.at_level(logging.INFO):
        await onboarding.onboarding_poll_answer(update, context)
    assert "Onboarding poll result from 42: 👎" in caplog.text
    assert "p1" not in context.bot_data.get("onboarding_polls", {})

