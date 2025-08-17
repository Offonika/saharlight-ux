from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.photo_handlers as photo_handlers


class DummyMessage:
    def __init__(self) -> None:
        self.texts: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)


@pytest.mark.asyncio
async def test_photo_handler_no_user_data() -> None:
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=None),
    )
    result = await photo_handlers.photo_handler(update, context)
    assert result == photo_handlers.END


@pytest.mark.asyncio
async def test_photo_handler_no_message_no_query() -> None:
    update = cast(Update, SimpleNamespace(message=None, callback_query=None, effective_user=SimpleNamespace(id=1)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    result = await photo_handlers.photo_handler(update, context)
    assert result == photo_handlers.END


@pytest.mark.asyncio
async def test_photo_handler_waiting_flag() -> None:
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={photo_handlers.WAITING_GPT_FLAG: True}),
    )
    result = await photo_handlers.photo_handler(update, context)
    assert result == photo_handlers.END
    assert message.texts == ["⏳ Уже обрабатываю фото, подождите…"]


class NoPhotoMessage(DummyMessage):
    def __init__(self) -> None:
        super().__init__()
        self.photo = None


@pytest.mark.asyncio
async def test_photo_handler_not_image() -> None:
    message = NoPhotoMessage()
    update = cast(Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    result = await photo_handlers.photo_handler(update, context)
    assert result == photo_handlers.END
    assert message.texts == ["❗ Файл не распознан как изображение."]

