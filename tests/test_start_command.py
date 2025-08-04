import os
os.environ.setdefault("DB_PASSWORD", "test")
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import diabetes.common_handlers as handlers
from diabetes.db import Base, Profile, User


class DummyMessage:
    def __init__(self):
        self.texts = []
        self.kwargs = []

    async def reply_text(self, text, **kwargs):
        self.texts.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_start_command_shows_profile_hint_only_once(monkeypatch):
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
    update = SimpleNamespace(
        message=message, effective_user=SimpleNamespace(id=1, first_name="Ann")
    )
    context = SimpleNamespace(user_data={})

    await handlers.start_command(update, context)

    # User created and greeting + hint sent
    with TestSession() as session:
        user = session.get(User, 1)
        assert user is not None
    assert len(message.texts) == 2
    assert message.kwargs[0]["reply_markup"] == "MK"
    assert "Рада видеть" in message.texts[0]
    assert "/profile" in message.texts[1]

    # Second call should not repeat the hint
    await handlers.start_command(update, context)
    assert len(message.texts) == 3
    assert sum("/profile" in t for t in message.texts) == 1


@pytest.mark.asyncio
async def test_start_command_without_hint_when_profile_complete(monkeypatch):
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import diabetes.gpt_client as gpt_client

    monkeypatch.setattr(gpt_client, "create_thread", lambda: "tid")

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(handlers, "menu_keyboard", "MK")

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="tid"))
        session.add(Profile(telegram_id=1, icr=10, cf=2, target_bg=5))
        session.commit()

    message = DummyMessage()
    update = SimpleNamespace(
        message=message, effective_user=SimpleNamespace(id=1, first_name="Ann")
    )
    context = SimpleNamespace(user_data={"thread_id": "tid"})

    await handlers.start_command(update, context)

    # Only greeting should be sent
    assert len(message.texts) == 1
    assert "/profile" not in message.texts[0]
    assert message.kwargs[0]["reply_markup"] == "MK"
    assert "Рада видеть" in message.texts[0]
