from types import SimpleNamespace
import os

import pytest
from telegram.ext import ConversationHandler, MessageHandler

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
import diabetes.openai_utils as openai_utils  # noqa: F401
from diabetes import dose_handlers


class DummyMessage:
    def __init__(self, text=""):
        self.text = text
        self.replies: list[str] = []
        self.kwargs: list[dict] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_sugar_val_back_cancels():
    message = DummyMessage("↩️ Назад")
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data={"pending_entry": {"foo": "bar"}})
    result = await dose_handlers.sugar_val(update, context)
    assert result == ConversationHandler.END
    assert message.replies and message.replies[-1] == "Отменено."
    assert context.user_data == {}


@pytest.mark.asyncio
async def test_cancel_command_clears_state():
    message = DummyMessage("/cancel")
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data={"pending_entry": {"foo": "bar"}})
    result = await dose_handlers.dose_cancel(update, context)
    assert result == ConversationHandler.END
    assert message.replies and message.replies[-1] == "Отменено."
    assert context.user_data == {}


def test_sugar_conv_has_back_fallback():
    fallbacks = dose_handlers.sugar_conv.fallbacks
    assert any(
        isinstance(h, MessageHandler)
        and h.callback is dose_handlers.dose_cancel
        and getattr(getattr(h, "filters", None), "pattern", None).pattern == "^↩️ Назад$"
        for h in fallbacks
    )

