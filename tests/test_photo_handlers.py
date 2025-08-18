import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.error import TelegramError
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
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    await photo_handlers.photo_prompt(update, context)
    assert any("фото" in t.lower() for t in message.texts)


@pytest.mark.asyncio
async def test_photo_handler_waiting_flag_returns_end() -> None:
    message = DummyMessage(photo=(SimpleNamespace(file_id="f", file_unique_id="u"),))
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={photo_handlers.WAITING_GPT_FLAG: True}),
    )
    result = await photo_handlers.photo_handler(update, context)
    assert result == photo_handlers.END
    assert message.texts and "подождите" in message.texts[0].lower()


@pytest.mark.asyncio
async def test_photo_handler_get_file_telegram_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    class DummyPhoto:
        file_id = "fid"
        file_unique_id = "uid"

    message = DummyMessage(photo=(DummyPhoto(),))
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )

    async def fake_get_file(file_id: str) -> Any:
        raise TelegramError("boom")

    dummy_bot = SimpleNamespace(get_file=fake_get_file)
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=dummy_bot, user_data={}),
    )

    monkeypatch.chdir(tmp_path)

    with caplog.at_level(logging.ERROR):
        result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.END
    assert message.texts == ["⚠️ Не удалось сохранить фото. Попробуйте ещё раз."]
    assert context.user_data is not None
    user_data = context.user_data
    assert photo_handlers.WAITING_GPT_FLAG not in user_data
    assert "[PHOTO] Failed to save photo" in caplog.text
