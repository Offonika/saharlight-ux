import os
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
    import diabetes.openai_utils  # noqa: F401
    import diabetes.common_handlers as handlers

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
