from types import SimpleNamespace
from pathlib import Path
from typing import Any, cast

import asyncio

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
    update = cast(
        Update,
        SimpleNamespace(message=None, callback_query=None, effective_user=SimpleNamespace(id=1)),
    )
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
async def test_photo_handler_not_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    orig = photo_handlers._clear_waiting_gpt

    def wrapped(user_data: dict[str, Any]) -> None:
        nonlocal calls
        calls += 1
        orig(user_data)

    monkeypatch.setattr(photo_handlers, "_clear_waiting_gpt", wrapped)
    message = NoPhotoMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    result = await photo_handlers.photo_handler(update, context)
    assert result == photo_handlers.END
    assert message.texts == ["❗ Файл не распознан как изображение."]
    assert context.user_data is not None
    assert photo_handlers.WAITING_GPT_FLAG not in context.user_data
    assert photo_handlers.WAITING_GPT_TIMESTAMP not in context.user_data
    assert calls == 1


@pytest.mark.asyncio
async def test_photo_handler_timeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class DummyPhoto:
        file_id = "fid"
        file_unique_id = "uid"

    class DummyMessage:
        def __init__(self) -> None:
            self.photo = (DummyPhoto(),)
            self.texts: list[str] = []

        async def reply_text(self, text: str, **kwargs: Any) -> None:
            self.texts.append(text)

    async def fake_get_file(file_id: str) -> Any:
        class File:
            async def download_as_bytearray(self) -> bytearray:
                return bytearray(b"img")

        return File()

    async def fake_send_message(**kwargs: Any) -> Any:
        raise asyncio.TimeoutError

    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)))
    dummy_bot = SimpleNamespace(get_file=fake_get_file)
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=dummy_bot, user_data={"thread_id": "tid"}),
    )

    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)

    calls = 0
    orig = photo_handlers._clear_waiting_gpt

    def wrapped(user_data: dict[str, Any]) -> None:
        nonlocal calls
        calls += 1
        orig(user_data)

    monkeypatch.setattr(photo_handlers, "_clear_waiting_gpt", wrapped)
    result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.END
    assert message.texts == ["⚠️ Превышено время ожидания ответа. Попробуйте ещё раз."]
    assert context.user_data is not None
    assert photo_handlers.WAITING_GPT_FLAG not in context.user_data
    assert photo_handlers.WAITING_GPT_TIMESTAMP not in context.user_data
    assert calls == 1


@pytest.mark.asyncio
async def test_photo_handler_download_os_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class DummyPhoto:
        file_id = "fid"
        file_unique_id = "uid"

    message = DummyMessage()
    message.photo = (DummyPhoto(),)
    update = cast(Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)))

    async def fake_get_file(file_id: str) -> Any:
        class File:
            async def download_as_bytearray(self) -> bytearray:
                raise OSError("boom")

        return File()

    dummy_bot = SimpleNamespace(get_file=fake_get_file)
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=dummy_bot, user_data={}),
    )

    result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.END
    assert message.texts == ["⚠️ Не удалось скачать фото. Попробуйте ещё раз."]
    assert photo_handlers.WAITING_GPT_FLAG not in context.user_data
    assert photo_handlers.WAITING_GPT_TIMESTAMP not in context.user_data
