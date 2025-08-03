import datetime
import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


class DummyMessage:
    def __init__(self):
        self.texts = []

    async def reply_text(self, text, **kwargs):
        self.texts.append(text)


class DummyQuery:
    def __init__(self, data):
        self.data = data
        self.edited = []

    async def answer(self):
        pass

    async def edit_message_text(self, text, **kwargs):
        self.edited.append(text)


@pytest.mark.asyncio
async def test_profile_command_commit_failure(monkeypatch, caplog):
    import os

    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["OPENAI_ASSISTANT_ID"] = "asst_test"
    import diabetes.openai_utils  # noqa: F401
    import diabetes.handlers as handlers

    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = None
    session.get.return_value = None
    session.add = MagicMock()
    session.commit.side_effect = Exception("fail")
    session.rollback = MagicMock()

    monkeypatch.setattr(handlers, "SessionLocal", lambda: session)

    message = DummyMessage()
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(args=["10", "2", "6"], user_data={})

    with caplog.at_level(logging.ERROR):
        await handlers.profile_command(update, context)

    assert session.rollback.called
    assert "DB commit failed" in caplog.text


@pytest.mark.asyncio
async def test_callback_router_commit_failure(monkeypatch, caplog):
    import os

    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["OPENAI_ASSISTANT_ID"] = "asst_test"
    import diabetes.openai_utils  # noqa: F401
    import diabetes.handlers as handlers

    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = None
    session.add = MagicMock()
    session.commit.side_effect = Exception("fail")
    session.rollback = MagicMock()

    monkeypatch.setattr(handlers, "SessionLocal", lambda: session)

    pending_entry = {
        "telegram_id": 1,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
    }
    query = DummyQuery("confirm_entry")
    update = SimpleNamespace(callback_query=query)
    context = SimpleNamespace(user_data={"pending_entry": pending_entry})

    with caplog.at_level(logging.ERROR):
        await handlers.callback_router(update, context)

    assert session.rollback.called
    assert "DB commit failed" in caplog.text
    assert query.edited  # message was edited despite failure
