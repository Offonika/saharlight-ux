import os
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from diabetes.db import Base, User
import diabetes.common_handlers as handlers


class DummyMessage:
    def __init__(self):
        self.texts = []
        self.kwargs = []

    async def reply_text(self, text, **kwargs):
        self.texts.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_start_command_creates_user_and_shows_menu(monkeypatch):
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import diabetes.gpt_client as gpt_client
    monkeypatch.setattr(gpt_client, "create_thread", lambda: "tid")

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(handlers, "menu_keyboard", "MK")

    message = DummyMessage()
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1, first_name="Ann"))
    context = SimpleNamespace(user_data={})

    await handlers.start_command(update, context)

    with TestSession() as session:
        user = session.get(User, 1)
        assert user is not None
        assert user.thread_id == "tid"

    assert context.user_data["thread_id"] == "tid"
    assert any("Выберите" in t for t in message.texts)
    assert message.kwargs[0]["reply_markup"] == "MK"
