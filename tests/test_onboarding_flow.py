import os
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from telegram.ext import ConversationHandler

from services.api.app.diabetes.services.db import Base, User
from tests.helpers import make_context, make_update


class DummyMessage:
    def __init__(self):
        self.texts: list[str] = []
        self.photos: list[tuple[Any, str | None]] = []
        self.polls: list[tuple[str, list[str]]] = []
        self.markups: list[Any] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.markups.append(kwargs.get("reply_markup"))

    async def reply_photo(
        self, photo: Any, caption: str | None = None, **kwargs: Any
    ) -> None:
        self.photos.append((photo, caption))
        self.markups.append(kwargs.get("reply_markup"))

    async def reply_poll(
        self, question: str, options: list[str], **kwargs: Any
    ) -> SimpleNamespace:
        self.polls.append((question, options))
        self.markups.append(kwargs.get("reply_markup"))
        return SimpleNamespace(poll=SimpleNamespace(id="p1"))

    async def delete(self) -> None:
        pass


class DummyQuery:
    def __init__(self, message, data):
        self.message = message
        self.data = data

    async def answer(self) -> None:
        pass


@pytest.mark.asyncio
async def test_onboarding_flow(monkeypatch) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")

    import services.api.app.diabetes.handlers.onboarding_handlers as onboarding
    import services.api.app.diabetes.services.gpt_client as gpt_client

    monkeypatch.setattr(gpt_client, "create_thread", lambda: "tid")

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(onboarding, "SessionLocal", TestSession)
    monkeypatch.setattr(onboarding, "menu_keyboard", "MK")

    message = DummyMessage()
    update = make_update(
        message=message, effective_user=SimpleNamespace(id=1, first_name="Ann")
    )
    context = make_context(user_data={}, bot_data={})

    state = await onboarding.start_command(update, context)
    assert state == onboarding.ONB_PROFILE_ICR
    assert "1/3" in message.texts[-1]

    update.message.text = "10"
    state = await onboarding.onboarding_icr(update, context)
    assert state == onboarding.ONB_PROFILE_CF

    update.message.text = "3"
    state = await onboarding.onboarding_cf(update, context)
    assert state == onboarding.ONB_PROFILE_TARGET

    update.message.text = "6"
    state = await onboarding.onboarding_target(update, context)
    assert state == onboarding.ONB_PROFILE_TZ

    update.message.text = "Europe/Moscow"
    state = await onboarding.onboarding_timezone(update, context)
    assert state == onboarding.ONB_DEMO
    assert message.photos

    query = DummyQuery(message, "onb_next")
    update_cb = make_update(callback_query=query, effective_user=SimpleNamespace(id=1))
    state = await onboarding.onboarding_demo_next(update_cb, context)
    assert state == onboarding.ONB_REMINDERS
    assert "3/3" in message.texts[-1]

    query2 = DummyQuery(message, "onb_rem_no")
    update_cb2 = make_update(callback_query=query2, effective_user=SimpleNamespace(id=1))
    state = await onboarding.onboarding_reminders(update_cb2, context)
    assert state == ConversationHandler.END
    assert message.polls

    with TestSession() as session:
        user = session.get(User, 1)
        assert user.onboarding_complete is True

    message2 = DummyMessage()
    update2 = make_update(
        message=message2, effective_user=SimpleNamespace(id=1, first_name="Ann")
    )
    context2 = make_context(user_data={}, bot_data={})
    state2 = await onboarding.start_command(update2, context2)
    assert state2 == ConversationHandler.END
    assert any("Выберите" in t for t in message2.texts)
