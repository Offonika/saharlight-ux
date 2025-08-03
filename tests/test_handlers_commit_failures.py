import datetime
import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError
import diabetes.profile_handlers as profile_handlers
import diabetes.common_handlers as common_handlers


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

    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = None
    session.get.return_value = None
    session.add = MagicMock()
    session.commit.side_effect = SQLAlchemyError("fail")
    session.rollback = MagicMock()

    monkeypatch.setattr(profile_handlers, "SessionLocal", lambda: session)

    message = DummyMessage()
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(args=["10", "2", "6"], user_data={})

    with caplog.at_level(logging.ERROR):
        with pytest.raises(SQLAlchemyError):
            await profile_handlers.profile_command(update, context)

    assert session.rollback.called
    assert "DB commit failed" in caplog.text


@pytest.mark.asyncio
async def test_callback_router_commit_failure(monkeypatch, caplog):
    import os

    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["OPENAI_ASSISTANT_ID"] = "asst_test"
    import diabetes.openai_utils  # noqa: F401

    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = None
    session.add = MagicMock()
    session.commit.side_effect = SQLAlchemyError("fail")
    session.rollback = MagicMock()

    monkeypatch.setattr(common_handlers, "SessionLocal", lambda: session)

    pending_entry = {
        "telegram_id": 1,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
    }
    query = DummyQuery("confirm_entry")
    update = SimpleNamespace(callback_query=query)
    context = SimpleNamespace(user_data={"pending_entry": pending_entry})

    with caplog.at_level(logging.ERROR):
        with pytest.raises(SQLAlchemyError):
            await common_handlers.callback_router(update, context)

    assert session.rollback.called
    assert "DB commit failed" in caplog.text
    assert not query.edited  # message was not edited due to failure
