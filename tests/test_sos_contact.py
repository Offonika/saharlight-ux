import pytest
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from diabetes.db import Base, User, Profile
import diabetes.sos_handlers as sos_handlers
import diabetes.alert_handlers as alert_handlers
from diabetes.common_handlers import commit_session


class DummyMessage:
    def __init__(self, text):
        self.text = text
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


class DummyBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text):
        self.sent.append((chat_id, text))


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

    bot = DummyBot()
    update_alert = SimpleNamespace(
        effective_user=SimpleNamespace(id=1, first_name="Ivan")
    )
    context = SimpleNamespace(bot=bot)
    monkeypatch.setattr(alert_handlers, "get_coords_and_link", lambda: ("0,0", "link"))

    for _ in range(3):
        await alert_handlers.check_alert(update_alert, context, 3)

    msg = "⚠️ У Ivan критический сахар 3 ммоль/л. 0,0 link"
    assert bot.sent == [(1, msg), ("@alice", msg)]
