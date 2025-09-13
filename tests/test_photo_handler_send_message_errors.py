from types import SimpleNamespace
from typing import Any, Type, cast

import httpx
import pytest
from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.photo_handlers as photo_handlers


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


@pytest.mark.asyncio
@pytest.mark.parametrize("exc_cls", [RuntimeError, httpx.HTTPError])
async def test_photo_handler_send_message_errors(monkeypatch: pytest.MonkeyPatch, exc_cls: Type[Exception]) -> None:
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)))
    dummy_bot = SimpleNamespace(get_file=fake_get_file)
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=dummy_bot, user_data={"thread_id": "tid"}),
    )

    async def fake_send_message(**kwargs: Any) -> Any:
        raise exc_cls("boom")

    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)

    result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.END
    assert message.texts == ["⚠️ Vision не смог обработать фото. Попробуйте ещё раз."]
    assert context.user_data is not None
    assert photo_handlers.WAITING_GPT_FLAG not in context.user_data
    assert photo_handlers.WAITING_GPT_TIMESTAMP not in context.user_data
