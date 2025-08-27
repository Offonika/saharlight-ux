import os
from types import SimpleNamespace
from typing import Any

import pytest
from telegram.ext import CommandHandler
from tests.helpers import make_context, make_update

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
from services.api.app.diabetes.handlers import dose_handlers


class DummyMessage:
    def __init__(self, text: str = ""):
        self.text = text
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


def _get_menu_handler(fallbacks):
    return next(
        h
        for h in fallbacks
        if isinstance(h, CommandHandler) and "menu" in getattr(h, "commands", [])
    )


@pytest.mark.asyncio
async def test_sugar_conv_menu_then_photo() -> None:
    handler = _get_menu_handler(dose_handlers.sugar_conv.fallbacks)
    message = DummyMessage("/menu")
    update = make_update(message=message, effective_user=SimpleNamespace(id=1))
    context = make_context(user_data={"pending_entry": {"foo": "bar"}})

    await handler.callback(update, context)

    assert message.replies[0] == "Отменено."
    assert any("выберите" in r.lower() for r in message.replies[1:])
    assert context.user_data == {}

    next_message = DummyMessage("📷 Фото еды")
    next_update = make_update(
        message=next_message, effective_user=SimpleNamespace(id=1)
    )
    await dose_handlers.photo_prompt(next_update, context)
    assert any("фото" in r.lower() for r in next_message.replies)

@pytest.mark.asyncio
async def test_dose_conv_menu_then_photo() -> None:
    handler = _get_menu_handler(dose_handlers.dose_conv.fallbacks)
    message = DummyMessage("/menu")
    update = make_update(message=message, effective_user=SimpleNamespace(id=1))
    context = make_context(user_data={"pending_entry": {"foo": "bar"}})

    await handler.callback(update, context)

    assert message.replies[0] == "Отменено."
    assert any("выберите" in r.lower() for r in message.replies[1:])
    assert context.user_data == {}

    next_message = DummyMessage("📷 Фото еды")
    next_update = make_update(
        message=next_message, effective_user=SimpleNamespace(id=1)
    )
    await dose_handlers.photo_prompt(next_update, context)
    assert any("фото" in r.lower() for r in next_message.replies)

