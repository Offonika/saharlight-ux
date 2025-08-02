import pytest
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from diabetes.db import Base, User


class DummyMessage:
    def __init__(self):
        self.texts = []

    async def reply_text(self, text, **kwargs):
        self.texts.append(text)


@pytest.mark.asyncio
async def test_profile_command_and_view(monkeypatch):
    import os
    os.environ["OPENAI_API_KEY"] = "test"
    import diabetes.handlers as handlers

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    monkeypatch.setattr(handlers, "SessionLocal", TestSession)

    with TestSession() as session:
        session.add(User(telegram_id=123, thread_id="t"))
        session.commit()

    message = DummyMessage()
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=123))
    context = SimpleNamespace(args=["8", "3", "6"], user_data={})

    await handlers.profile_command(update, context)
    assert "ИКХ: 8.0 г/ед." in message.texts[0]
    assert "КЧ: 3.0 ммоль/л" in message.texts[0]

    message2 = DummyMessage()
    update2 = SimpleNamespace(message=message2, effective_user=SimpleNamespace(id=123))
    context2 = SimpleNamespace(user_data={})

    await handlers.profile_view(update2, context2)
    assert "ИКХ: 8.0 г/ед." in message2.texts[0]
    assert "КЧ: 3.0 ммоль/л" in message2.texts[0]
