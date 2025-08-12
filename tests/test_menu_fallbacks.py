from types import SimpleNamespace
import os

import pytest
from telegram.ext import CommandHandler

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
import apps.telegram_bot.openai_utils as openai_utils  # noqa: F401
from apps.telegram_bot import dose_handlers


class DummyMessage:
    def __init__(self, text=""):
        self.text = text
        self.replies: list[str] = []
        self.kwargs: list[dict] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)
        self.kwargs.append(kwargs)


def _get_menu_handler(fallbacks):
    return next(
        h
        for h in fallbacks
        if isinstance(h, CommandHandler) and "menu" in getattr(h, "commands", [])
    )


@pytest.mark.asyncio
async def test_sugar_conv_menu_then_photo():
    handler = _get_menu_handler(dose_handlers.sugar_conv.fallbacks)
    message = DummyMessage("/menu")
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data={"pending_entry": {"foo": "bar"}})

    await handler.callback(update, context)

    assert message.replies[0] == "Отменено."
    assert any("выберите" in r.lower() for r in message.replies[1:])
    assert context.user_data == {}

    next_message = DummyMessage("📷 Фото еды")
    next_update = SimpleNamespace(
        message=next_message, effective_user=SimpleNamespace(id=1)
    )
    await dose_handlers.photo_prompt(next_update, context)
    assert any("фото" in r.lower() for r in next_message.replies)

@pytest.mark.asyncio
async def test_dose_conv_menu_then_photo():
    handler = _get_menu_handler(dose_handlers.dose_conv.fallbacks)
    message = DummyMessage("/menu")
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data={"pending_entry": {"foo": "bar"}})

    await handler.callback(update, context)

    assert message.replies[0] == "Отменено."
    assert any("выберите" in r.lower() for r in message.replies[1:])
    assert context.user_data == {}

    next_message = DummyMessage("📷 Фото еды")
    next_update = SimpleNamespace(
        message=next_message, effective_user=SimpleNamespace(id=1)
    )
    await dose_handlers.photo_prompt(next_update, context)
    assert any("фото" in r.lower() for r in next_message.replies)

