import os
import re
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, call

import pytest
from typing import cast

from .context_stub import AlertContext, ContextStub

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram.ext import ApplicationBuilder, CallbackContext, MessageHandler
from telegram import Bot

from services.api.app.diabetes.services.db import Base, User, Profile
import services.api.app.diabetes.handlers.sos_handlers as sos_handlers
import services.api.app.diabetes.handlers.alert_handlers as alert_handlers
import services.api.app.diabetes.handlers.registration as handlers
from services.api.app.diabetes.services.repository import commit
from services.api.app.diabetes.utils.ui import menu_keyboard
from tests.helpers import make_context, make_update


class DummyMessage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)


@pytest.fixture
def test_session(monkeypatch: Any) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(sos_handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(alert_handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(sos_handlers, "commit", commit)
    monkeypatch.setattr(alert_handlers, "commit", commit)
    return TestSession


@pytest.mark.asyncio
@pytest.mark.parametrize("contact", ["@alice", "123456"])
async def test_soscontact_stores_contact(test_session: Any, contact: Any) -> None:
    with test_session() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Profile(telegram_id=1))
        session.commit()

    message = DummyMessage(contact)
    update = make_update(message=message, effective_user=SimpleNamespace(id=1))
    context = make_context()

    result = await sos_handlers.sos_contact_save(update, context)

    assert result == sos_handlers.ConversationHandler.END
    assert message.replies == ["✅ Контакт для SOS сохранён."]

    with test_session() as session:
        profile = session.get(Profile, 1)
        assert profile.sos_contact == contact


@pytest.mark.asyncio
async def test_alert_notifies_user_and_contact(test_session: Any, monkeypatch: Any) -> None:
    with test_session() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Profile(telegram_id=1, low_threshold=4, high_threshold=8))
        session.commit()

    # Save SOS contact via handler
    message = DummyMessage("@alice")
    update = make_update(message=message, effective_user=SimpleNamespace(id=1))
    await sos_handlers.sos_contact_save(update, SimpleNamespace())

    update_alert = make_update(
        effective_user=SimpleNamespace(id=1, first_name="Ivan")
    )
    context: AlertContext = ContextStub(bot=cast(Bot, SimpleNamespace()))
    send_mock = AsyncMock()
    monkeypatch.setattr(context.bot, "send_message", send_mock, raising=False)
    async def fake_get_coords_and_link() -> None:
        return ("0,0", "link")

    monkeypatch.setattr(alert_handlers, "get_coords_and_link", fake_get_coords_and_link)

    for _ in range(3):
        await alert_handlers.check_alert(
            update_alert, cast(CallbackContext[Any, Any, Any, Any], context), 3
        )

    msg = "⚠️ У Ivan критический сахар 3 ммоль/л. 0,0 link"
    assert send_mock.await_args_list == [
        call(chat_id=1, text=msg),
        call(chat_id="@alice", text=msg),
    ]


@pytest.mark.asyncio
async def test_alert_skips_phone_contact(test_session: Any, monkeypatch: Any) -> None:
    with test_session() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(
            Profile(
                telegram_id=1,
                low_threshold=4,
                high_threshold=8,
                sos_contact="+123",
                sos_alerts_enabled=True,
            )
        )
        session.commit()

    update_alert = make_update(
        effective_user=SimpleNamespace(id=1, first_name="Ivan")
    )
    context: AlertContext = ContextStub(bot=cast(Bot, SimpleNamespace()))
    send_mock = AsyncMock()
    monkeypatch.setattr(context.bot, "send_message", send_mock, raising=False)

    async def fake_get_coords_and_link() -> None:
        return ("0,0", "link")

    monkeypatch.setattr(alert_handlers, "get_coords_and_link", fake_get_coords_and_link)

    for _ in range(3):
        await alert_handlers.check_alert(
            update_alert, cast(CallbackContext[Any, Any, Any, Any], context), 3
        )

    msg = "⚠️ У Ivan критический сахар 3 ммоль/л. 0,0 link"
    assert send_mock.await_args_list == [call(chat_id=1, text=msg)]


@pytest.mark.asyncio
async def test_sos_contact_menu_button_starts_conv(monkeypatch: Any) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401

    button_texts = [btn.text for row in menu_keyboard.keyboard for btn in row]
    assert "🆘 SOS контакт" in button_texts

    app = ApplicationBuilder().token("TESTTOKEN").build()
    handlers.register_handlers(app)
    sos_handler = next(
        h
        for h in app.handlers[0]
        if isinstance(h, MessageHandler) and h.callback is sos_handlers.sos_contact_start
    )
    pattern = sos_handler.filters.pattern.pattern
    assert re.fullmatch(pattern, "🆘 SOS контакт")

    message = DummyMessage("🆘 SOS контакт")
    update = make_update(message=message)
    context = make_context()
    state = await sos_handler.callback(update, context)

    assert state == sos_handlers.SOS_CONTACT
    assert message.replies == [
        "Введите контакт в Telegram (@username). Телефоны не поддерживаются."
    ]
