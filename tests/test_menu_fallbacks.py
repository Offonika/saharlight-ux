import os
from types import SimpleNamespace
from typing import Any, Sequence, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext, CommandHandler

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
from services.api.app.diabetes.handlers import dose_calc
from services.api.app.diabetes.utils.ui import PHOTO_BUTTON_TEXT


class DummyMessage:
    def __init__(self, text: str = "") -> None:
        self.text: str = text
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


def _get_menu_handler(
    fallbacks: Sequence[CommandHandler[Any, Any]],
) -> CommandHandler[Any, Any]:
    return next(h for h in fallbacks if "menu" in getattr(h, "commands", []))


@pytest.mark.asyncio
async def test_sugar_conv_menu_then_photo() -> None:
    handler = _get_menu_handler(
        cast(
            Sequence[CommandHandler[Any, Any]],
            [
                h
                for h in dose_calc.sugar_conv.fallbacks
                if isinstance(h, CommandHandler)
            ],
        )
    )
    message = DummyMessage("/menu")
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"pending_entry": {"foo": "bar"}}),
    )

    await handler.callback(update, context)

    assert message.replies[0] == "Отменено."
    assert any("выберите" in r.lower() for r in message.replies[1:])
    assert context.user_data == {}

    next_message = DummyMessage(PHOTO_BUTTON_TEXT)
    next_update = cast(
        Update,
        SimpleNamespace(message=next_message, effective_user=SimpleNamespace(id=1)),
    )
    await dose_calc.photo_prompt(next_update, context)
    assert any("фото" in r.lower() for r in next_message.replies)


@pytest.mark.asyncio
async def test_dose_conv_menu_then_photo() -> None:
    handler = _get_menu_handler(
        cast(
            Sequence[CommandHandler[Any, Any]],
            [h for h in dose_calc.dose_conv.fallbacks if isinstance(h, CommandHandler)],
        )
    )
    message = DummyMessage("/menu")
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"pending_entry": {"foo": "bar"}}),
    )

    await handler.callback(update, context)

    assert message.replies[0] == "Отменено."
    assert any("выберите" in r.lower() for r in message.replies[1:])
    assert context.user_data == {}

    next_message = DummyMessage(PHOTO_BUTTON_TEXT)
    next_update = cast(
        Update,
        SimpleNamespace(message=next_message, effective_user=SimpleNamespace(id=1)),
    )
    await dose_calc.photo_prompt(next_update, context)
    assert any("фото" in r.lower() for r in next_message.replies)
