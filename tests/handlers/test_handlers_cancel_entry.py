import os
import logging
from types import SimpleNamespace

import pytest


class DummyMessage:
    def __init__(self):
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append((text, kwargs))


class DummyQuery:
    def __init__(self, data):
        self.data = data
        self.edited = []
        self.edit_kwargs = []
        self.message = DummyMessage()

    async def answer(self):
        pass

    async def edit_message_text(self, text, **kwargs):
        self.edited.append(text)
        self.edit_kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_callback_router_cancel_entry_sends_menu():
    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["OPENAI_ASSISTANT_ID"] = "asst_test"
    import diabetes.utils.openai_utils  # noqa: F401
    import diabetes.handlers.common_handlers as handlers

    query = DummyQuery("cancel_entry")
    update = SimpleNamespace(callback_query=query)
    context = SimpleNamespace(user_data={"pending_entry": {"telegram_id": 1}})

    await handlers.callback_router(update, context)

    assert query.edited == ["❌ Запись отменена."]
    assert not query.edit_kwargs[0] or "reply_markup" not in query.edit_kwargs[0]
    assert len(query.message.replies) == 1
    text, kwargs = query.message.replies[0]
    assert kwargs["reply_markup"] == handlers.menu_keyboard
    assert "pending_entry" not in context.user_data


@pytest.mark.asyncio
async def test_callback_router_invalid_entry_id(caplog):
    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["OPENAI_ASSISTANT_ID"] = "asst_test"
    import diabetes.utils.openai_utils  # noqa: F401
    import diabetes.handlers.common_handlers as handlers

    query = DummyQuery("del:abc")
    update = SimpleNamespace(callback_query=query)
    context = SimpleNamespace(user_data={})

    with caplog.at_level(logging.WARNING):
        await handlers.callback_router(update, context)

    assert query.edited == ["Некорректный идентификатор записи."]
    assert "Invalid entry_id in callback data" in caplog.text


@pytest.mark.asyncio
async def test_callback_router_unknown_data(caplog):
    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["OPENAI_ASSISTANT_ID"] = "asst_test"
    import diabetes.utils.openai_utils  # noqa: F401
    import diabetes.handlers.common_handlers as handlers

    query = DummyQuery("foo")
    update = SimpleNamespace(callback_query=query)
    context = SimpleNamespace(user_data={})

    with caplog.at_level(logging.WARNING):
        await handlers.callback_router(update, context)

    assert query.edited == ["Команда не распознана"]
    assert "Unrecognized callback data" in caplog.text


@pytest.mark.asyncio
async def test_callback_router_ignores_reminder_action():
    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["OPENAI_ASSISTANT_ID"] = "asst_test"
    import diabetes.utils.openai_utils  # noqa: F401
    import diabetes.handlers.common_handlers as handlers

    query = DummyQuery("rem_toggle:1")
    update = SimpleNamespace(callback_query=query)
    context = SimpleNamespace(user_data={"pending_entry": {}})

    await handlers.callback_router(update, context)

    assert query.edited == []
    assert "pending_entry" in context.user_data
