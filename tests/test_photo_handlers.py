import logging
import datetime
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import CallbackContext
from unittest.mock import AsyncMock

import services.api.app.diabetes.handlers.photo_handlers as photo_handlers
import services.api.app.diabetes.utils.functions as functions


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
async def test_photo_handler_clears_stale_waiting_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    old_ts = datetime.datetime.now(datetime.timezone.utc) - photo_handlers.WAITING_GPT_TIMEOUT - datetime.timedelta(seconds=1)
    user_data = {
        photo_handlers.WAITING_GPT_FLAG: True,
        photo_handlers.WAITING_GPT_TIMESTAMP: old_ts,
        "thread_id": "tid",
    }
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data),
    )

    async def fake_send_message(**kwargs: Any) -> Any:
        raise ValueError("fail")

    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)
    result = await photo_handlers.photo_handler(update, context, file_bytes=b"img")

    assert result == photo_handlers.END
    assert message.texts == ["⚠️ Не удалось распознать фото. Попробуйте ещё раз."]
    assert photo_handlers.WAITING_GPT_FLAG not in user_data
    assert photo_handlers.WAITING_GPT_TIMESTAMP not in user_data


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

    with caplog.at_level(logging.ERROR):
        result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.END
    assert message.texts == ["⚠️ Не удалось скачать фото. Попробуйте ещё раз."]
    assert context.user_data is not None
    user_data = context.user_data
    assert photo_handlers.WAITING_GPT_FLAG not in user_data
    assert photo_handlers.WAITING_GPT_TIMESTAMP not in user_data
    assert "[PHOTO] Failed to download photo" in caplog.text


@pytest.mark.asyncio
async def test_photo_handler_telegram_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
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
        raise TelegramError("boom")

    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    dummy_bot = SimpleNamespace(get_file=fake_get_file)
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=dummy_bot, user_data={"thread_id": "tid"}),
    )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)

    result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.END
    assert message.texts == ["⚠️ Произошла ошибка Telegram. Попробуйте ещё раз."]
    assert context.user_data is not None
    assert photo_handlers.WAITING_GPT_FLAG not in context.user_data


@pytest.mark.asyncio
async def test_photo_handler_mapping_proxy_mutable_user_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=MappingProxyType({"thread_id": "tid"})),
    )

    async def fake_send_message(**kwargs: Any) -> Any:
        raise ValueError("fail")

    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)
    result = await photo_handlers.photo_handler(update, context, file_bytes=b"img")

    assert result == photo_handlers.END
    user_data = photo_handlers._get_mutable_user_data(context)
    assert isinstance(user_data, dict)
    assert photo_handlers.WAITING_GPT_FLAG not in user_data
    assert photo_handlers.WAITING_GPT_TIMESTAMP not in user_data


@pytest.mark.asyncio
async def test_photo_handler_pending_entry_mapping_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class StatusMessage:
        async def delete(self) -> None:
            pass

    class DummyMessage2:
        def __init__(self) -> None:
            self.texts: list[str] = []
            self.chat_id = 1

        async def reply_text(self, text: str, **kwargs: Any) -> Any:
            self.texts.append(text)
            if text.startswith("🔍"):
                return StatusMessage()
            return None

    message = DummyMessage2()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            bot=SimpleNamespace(send_chat_action=AsyncMock()),
            user_data=MappingProxyType({"thread_id": "tid"}),
        ),
    )

    class Run:
        status = "completed"
        thread_id = "tid"
        id = "rid"

    async def fake_send_message(**kwargs: Any) -> Run:
        return Run()

    class Messages:
        data = [
            SimpleNamespace(
                role="assistant",
                content=[SimpleNamespace(text=SimpleNamespace(value="text"))],
            )
        ]

    class DummyClient:
        beta = SimpleNamespace(
            threads=SimpleNamespace(
                messages=SimpleNamespace(
                    list=lambda thread_id, run_id=None: Messages()
                )
            )
        )

    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)
    monkeypatch.setattr(photo_handlers, "_get_client", lambda: DummyClient())
    monkeypatch.setattr(
        photo_handlers,
        "extract_nutrition_info",
        lambda text: functions.NutritionInfo(carbs_g=10, xe=0.5),
    )

    result = await photo_handlers.photo_handler(update, context, file_bytes=b"img")

    assert result == photo_handlers.PHOTO_SUGAR
    user_data = photo_handlers._get_mutable_user_data(context)
    assert isinstance(user_data, dict)
    pending = user_data.get("pending_entry")
    assert pending is not None
    assert pending["carbs_g"] == 10
    assert pending["xe"] == 0.5
    assert photo_handlers.WAITING_GPT_FLAG not in user_data
