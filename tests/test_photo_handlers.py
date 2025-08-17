from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.photo_handlers as photo_handlers


class DummyMessage:
    def __init__(self, photo: tuple[Any, ...] | None = None) -> None:
        self.photo: tuple[Any, ...] = () if photo is None else photo
        self.texts: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)


@pytest.mark.asyncio
async def test_photo_prompt_sends_message() -> None:
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]], SimpleNamespace())
    await photo_handlers.photo_prompt(update, context)
    assert any("фото" in t.lower() for t in message.texts)


@pytest.mark.asyncio
async def test_photo_handler_waiting_flag_returns_end() -> None:
    message = DummyMessage(photo=(SimpleNamespace(file_id="f", file_unique_id="u"),))
    update = cast(Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={photo_handlers.WAITING_GPT_FLAG: True}),
    )
    result = await photo_handlers.photo_handler(update, context)
    assert result == photo_handlers.ConversationHandler.END
    assert message.texts and "подождите" in message.texts[0].lower()
