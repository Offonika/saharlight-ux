import os
import re
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, call

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram.ext import ApplicationBuilder, MessageHandler

from diabetes.db import Base, User, Profile
import diabetes.sos_handlers as sos_handlers
import diabetes.alert_handlers as alert_handlers
import diabetes.common_handlers as handlers
from diabetes.common_handlers import commit_session
from diabetes.ui import menu_keyboard


class DummyMessage:
    def __init__(self, text):
        self.text = text
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


@pytest.fixture
def test_session(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(sos_handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(alert_handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(sos_handlers, "commit_session", commit_session)
    monkeypatch.setattr(alert_handlers, "commit_session", commit_session)
    return TestSession


@pytest.mark.asyncio
async def test_soscontact_stores_contact(test_session):
    with test_session() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Profile(telegram_id=1))
        session.commit()

    message = DummyMessage("@alice")
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace()

    result = await sos_handlers.sos_contact_save(update, context)

    assert result == sos_handlers.ConversationHandler.END
    assert message.replies == ["✅ Контакт для SOS сохранён."]

    with test_session() as session:
        profile = session.get(Profile, 1)
        assert profile.sos_contact == "@alice"


@pytest.mark.asyncio
async def test_alert_notifies_user_and_contact(test_session, monkeypatch):
    with test_session() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Profile(telegram_id=1, low_threshold=4, high_threshold=8))
        session.commit()

    # Save SOS contact via handler
    message = DummyMessage("@alice")
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    await sos_handlers.sos_contact_save(update, SimpleNamespace())

    update_alert = SimpleNamespace(
        effective_user=SimpleNamespace(id=1, first_name="Ivan")
    )
    context = SimpleNamespace(bot=SimpleNamespace())
    send_mock = AsyncMock()
    monkeypatch.setattr(context.bot, "send_message", send_mock, raising=False)
    async def fake_get_coords_and_link():
        return ("0,0", "link")

    monkeypatch.setattr(alert_handlers, "get_coords_and_link", fake_get_coords_and_link)

    for _ in range(3):
        await alert_handlers.check_alert(update_alert, context, 3)

    msg = "⚠️ У Ivan критический сахар 3 ммоль/л. 0,0 link"
    assert send_mock.await_args_list == [
        call(chat_id=1, text=msg),
        call(chat_id="@alice", text=msg),
    ]


@pytest.mark.asyncio
async def test_alert_skips_phone_contact(test_session, monkeypatch):
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

    update_alert = SimpleNamespace(
        effective_user=SimpleNamespace(id=1, first_name="Ivan")
    )
    context = SimpleNamespace(bot=SimpleNamespace())
    send_mock = AsyncMock()
    monkeypatch.setattr(context.bot, "send_message", send_mock, raising=False)

    async def fake_get_coords_and_link():
        return ("0,0", "link")

    monkeypatch.setattr(alert_handlers, "get_coords_and_link", fake_get_coords_and_link)

    for _ in range(3):
        await alert_handlers.check_alert(update_alert, context, 3)

    msg = "⚠️ У Ivan критический сахар 3 ммоль/л. 0,0 link"
    assert send_mock.await_args_list == [call(chat_id=1, text=msg)]


@pytest.mark.asyncio
async def test_sos_contact_menu_button_starts_conv(monkeypatch):
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import diabetes.openai_utils as openai_utils  # noqa: F401

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
    update = SimpleNamespace(message=message)
    context = SimpleNamespace()
    state = await sos_handler.callback(update, context)

    assert state == sos_handlers.SOS_CONTACT
    assert message.replies == [
        "Введите контакт в Telegram (@username). Телефоны не поддерживаются."
    ]
