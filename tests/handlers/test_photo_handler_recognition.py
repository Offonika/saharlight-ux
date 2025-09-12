from __future__ import annotations

import os
import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from openai import OpenAIError
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import CallbackContext

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
import services.api.app.diabetes.handlers.photo_handlers as photo_handlers
import services.api.app.diabetes.utils.functions as functions


class DummyPhoto:
    file_id = "fid"
    file_unique_id = "uid"


class DummySession:
    def __init__(self) -> None:
        self.closed = False

    def __enter__(self) -> "DummySession":
        return self

    def __exit__(self, *args: Any) -> None:  # pragma: no cover - called automatically
        self.closed = True

    def get(self, model: Any, user_id: Any) -> Any:
        return None

    def add(self, obj: Any) -> None:
        self.obj = obj


@pytest.mark.asyncio
async def test_photo_handler_recognition_success_db_save(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class StatusMessage:
        def __init__(self) -> None:
            self.deleted = False

        async def delete(self) -> None:
            self.deleted = True

    class DummyMessage:
        def __init__(self) -> None:
            self.photo = (DummyPhoto(),)
            self.chat_id = 1
            self.texts: list[str] = []
            self.status = StatusMessage()

        async def reply_text(self, text: str, **kwargs: Any) -> Any:
            self.texts.append(text)
            if text.startswith("🔍"):
                return self.status
            return None

    class File:
        async def download_as_bytearray(self) -> bytearray:
            return bytearray(b"img")

    bot = SimpleNamespace(
        get_file=AsyncMock(return_value=File()),
        send_chat_action=AsyncMock(),
    )

    session = DummySession()
    commit_called = False

    def fake_commit(sess: Any) -> None:
        nonlocal commit_called
        commit_called = True

    def fake_create_thread_sync() -> str:
        return "tid"

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
                messages=SimpleNamespace(list=lambda thread_id: Messages())
            )
        )

    monkeypatch.setattr(photo_handlers, "SessionLocal", lambda: session)
    monkeypatch.setattr(photo_handlers, "create_thread_sync", fake_create_thread_sync)
    monkeypatch.setattr(photo_handlers, "commit", fake_commit)
    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)
    monkeypatch.setattr(photo_handlers, "_get_client", lambda: DummyClient())

    async def run_db_stub(fn, *args, sessionmaker, **kwargs):
        def wrapper() -> Any:
            with sessionmaker() as sess:
                return fn(sess, *args, **kwargs)

        return await asyncio.to_thread(wrapper)

    monkeypatch.setattr(photo_handlers, "run_db", run_db_stub)
    monkeypatch.setattr(
        photo_handlers,
        "extract_nutrition_info",
        lambda text: functions.NutritionInfo(carbs_g=10, xe=0.5),
    )

    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=bot, user_data={}),
    )
    monkeypatch.chdir(tmp_path)
    result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.PHOTO_SUGAR
    user_data = context.user_data
    assert user_data is not None
    pending = user_data.get("pending_entry")
    assert pending is not None
    assert pending["carbs_g"] == 10
    assert pending["xe"] == 0.5
    assert commit_called
    assert session.closed
    assert photo_handlers.WAITING_GPT_FLAG not in user_data
    assert message.status.deleted
    assert bot.send_chat_action.called


@pytest.mark.asyncio
async def test_photo_handler_openai_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyMessage:
        def __init__(self) -> None:
            self.photo = (DummyPhoto(),)
            self.texts: list[str] = []

        async def reply_text(self, text: str, **kwargs: Any) -> None:
            self.texts.append(text)

    async def fake_send_message(**kwargs: Any) -> None:
        raise OpenAIError("boom")

    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)

    class File:
        async def download_as_bytearray(self) -> bytearray:
            return bytearray(b"img")

    bot = SimpleNamespace(get_file=AsyncMock(return_value=File()))
    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=bot, user_data={"thread_id": "tid"}),
    )

    result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.END
    assert message.texts == ["⚠️ Vision не смог обработать фото. Попробуйте ещё раз."]
    user_data_err = context.user_data
    assert user_data_err is not None
    assert photo_handlers.WAITING_GPT_FLAG not in user_data_err


@pytest.mark.asyncio
async def test_photo_handler_fallback_parse_fail(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class StatusMessage:
        async def delete(self) -> None:
            pass

    class DummyMessage:
        def __init__(self) -> None:
            self.photo = (DummyPhoto(),)
            self.texts: list[str] = []

        async def reply_text(self, text: str, **kwargs: Any) -> Any:
            self.texts.append(text)
            if text.startswith("🔍"):
                return StatusMessage()
            return None

    async def fake_send_message(**kwargs: Any) -> Any:
        class Run:
            status = "completed"
            thread_id = "tid"
            id = "rid"

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
                messages=SimpleNamespace(list=lambda thread_id: Messages())
            )
        )

    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)
    monkeypatch.setattr(photo_handlers, "_get_client", lambda: DummyClient())
    monkeypatch.setattr(
        photo_handlers,
        "extract_nutrition_info",
        lambda t: functions.NutritionInfo(),
    )

    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )

    class File:
        async def download_as_bytearray(self) -> bytearray:
            return bytearray(b"x")

    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            bot=SimpleNamespace(get_file=AsyncMock(return_value=File())),
            user_data={"thread_id": "tid"},
        ),
    )
    monkeypatch.chdir(tmp_path)
    result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.END
    assert any("Не смог" in t for t in message.texts)
    user_data_fp = context.user_data
    assert user_data_fp is not None
    assert "pending_entry" not in user_data_fp
    assert photo_handlers.WAITING_GPT_FLAG not in user_data_fp


@pytest.mark.asyncio
async def test_photo_handler_missing_photo() -> None:
    class DummyMessage:
        def __init__(self) -> None:
            self.photo = None
            self.texts: list[str] = []

        async def reply_text(self, text: str, **kwargs: Any) -> None:
            self.texts.append(text)

    message = DummyMessage()
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


@pytest.mark.asyncio
async def test_doc_handler_invalid_file_type() -> None:
    document = SimpleNamespace(
        mime_type="text/plain",
        file_name="f.txt",
        file_unique_id="uid",
        file_id="fid",
    )
    message = SimpleNamespace(document=document)
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    bot = SimpleNamespace(get_file=AsyncMock())
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=bot, user_data={}),
    )

    result = await photo_handlers.doc_handler(update, context)

    assert result == photo_handlers.END
    assert not bot.get_file.called


@pytest.mark.asyncio
async def test_photo_handler_run_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class StatusMessage:
        def __init__(self) -> None:
            self.deleted = False

        async def delete(self) -> None:
            self.deleted = True

    class DummyMessage:
        def __init__(self) -> None:
            self.photo = (DummyPhoto(),)
            self.chat_id = 1
            self.texts: list[str] = []
            self.status: StatusMessage | None = None

        async def reply_text(self, text: str, **kwargs: Any) -> Any:
            self.texts.append(text)
            if text.startswith("🔍"):
                self.status = StatusMessage()
                return self.status
            return None

    class File:
        async def download_as_bytearray(self) -> bytearray:
            return bytearray(b"img")

    bot = SimpleNamespace(
        get_file=AsyncMock(return_value=File()),
        send_chat_action=AsyncMock(),
    )

    class Run:
        status = "in_progress"
        thread_id = "tid"
        id = "rid"

    async def fake_send_message(**kwargs: Any) -> Run:
        return Run()

    def fake_retrieve(*args: Any, **kwargs: Any) -> Run:
        return Run()

    class DummyClient:
        beta = SimpleNamespace(
            threads=SimpleNamespace(runs=SimpleNamespace(retrieve=fake_retrieve))
        )

    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)
    monkeypatch.setattr(photo_handlers, "_get_client", lambda: DummyClient())
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())

    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=bot, user_data={"thread_id": "tid"}),
    )
    monkeypatch.chdir(tmp_path)
    result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.END
    assert message.status is not None and message.status.deleted
    assert any("Время ожидания Vision истекло" in t for t in message.texts)
    user_data_timeout = context.user_data
    assert user_data_timeout is not None
    assert photo_handlers.WAITING_GPT_FLAG not in user_data_timeout


@pytest.mark.asyncio
async def test_doc_handler_valid_image(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    photo_mock = AsyncMock(return_value=photo_handlers.PHOTO_SUGAR)
    monkeypatch.setattr(photo_handlers, "photo_handler", photo_mock)

    class File:
        async def download_as_bytearray(self) -> bytearray:
            return bytearray(b"img")

    bot = SimpleNamespace(get_file=AsyncMock(return_value=File()))
    document = SimpleNamespace(
        mime_type="image/png",
        file_name="f.png",
        file_unique_id="uid",
        file_id="fid",
    )
    message = SimpleNamespace(document=document, photo=None)
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=bot, user_data={}),
    )
    monkeypatch.chdir(tmp_path)
    result = await photo_handlers.doc_handler(update, context)

    assert result == photo_handlers.PHOTO_SUGAR
    assert context.user_data == {}
    assert message.photo is None
    photo_mock.assert_awaited_once_with(update, context, file_bytes=b"img")


@pytest.mark.asyncio
async def test_photo_handler_typing_action_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class DummyMessage:
        def __init__(self) -> None:
            self.photo: tuple[Any, ...] = ()
            self.chat_id = 1
            self.texts: list[str] = []

        async def reply_text(self, text: str, **kwargs: Any) -> Any:
            self.texts.append(text)
            if text.startswith("🔍"):
                return SimpleNamespace(delete=AsyncMock())
            return None

    path = tmp_path / "img.jpg"
    path.write_bytes(b"img")

    async def fake_send_message(**kwargs: Any) -> Any:
        class Run:
            status = "completed"
            thread_id = "tid"
            id = "rid"

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
                messages=SimpleNamespace(list=lambda thread_id: Messages())
            )
        )

    bot = SimpleNamespace(send_chat_action=AsyncMock(side_effect=TelegramError("boom")))

    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)
    monkeypatch.setattr(photo_handlers, "_get_client", lambda: DummyClient())
    monkeypatch.setattr(
        photo_handlers,
        "extract_nutrition_info",
        lambda t: functions.NutritionInfo(carbs_g=10, xe=0.5),
    )

    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=bot, user_data={"thread_id": "tid"}),
    )
    result = await photo_handlers.photo_handler(
        update, context, file_bytes=path.read_bytes()
    )

    assert result == photo_handlers.PHOTO_SUGAR
    assert any("На фото" in t for t in message.texts)
    user_data_typing = context.user_data
    assert user_data_typing is not None
    assert photo_handlers.WAITING_GPT_FLAG not in user_data_typing


@pytest.mark.asyncio
async def test_photo_handler_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyMessage:
        def __init__(self) -> None:
            self.photo: tuple[Any, ...] = ()
            self.texts: list[str] = []

        async def reply_text(self, text: str, **kwargs: Any) -> None:
            self.texts.append(text)

    async def fake_send_message(**kwargs: Any) -> Any:
        class Run:
            status = "completed"
            thread_id = "tid"
            id = "rid"

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
                messages=SimpleNamespace(list=lambda thread_id: Messages())
            )
        )

    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)
    monkeypatch.setattr(photo_handlers, "_get_client", lambda: DummyClient())

    def raise_value(text: str) -> functions.NutritionInfo:
        raise ValueError("bad")

    monkeypatch.setattr(photo_handlers, "extract_nutrition_info", raise_value)

    path = Path("p.jpg")
    path.write_text("img")

    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"thread_id": "tid"}),
    )

    result = await photo_handlers.photo_handler(
        update, context, file_bytes=path.read_bytes()
    )

    assert result == photo_handlers.END
    assert message.texts[-1] == "⚠️ Не удалось распознать фото. Попробуйте ещё раз."
    user_data_val = context.user_data
    assert user_data_val is not None
    assert photo_handlers.WAITING_GPT_FLAG not in user_data_val


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "update_kwargs, context_kwargs",
    [
        (
            dict(
                message=SimpleNamespace(
                    document=SimpleNamespace(
                        mime_type="image/png",
                        file_name="f",
                        file_unique_id="u",
                        file_id="f",
                    )
                )
            ),
            dict(user_data=None),
        ),
        (dict(message=None), dict(user_data={})),
        (
            dict(
                message=SimpleNamespace(
                    document=SimpleNamespace(
                        mime_type="image/png",
                        file_name="f",
                        file_unique_id="u",
                        file_id="f",
                    )
                ),
                effective_user=None,
            ),
            dict(user_data={}),
        ),
        (dict(message=SimpleNamespace(document=None)), dict(user_data={})),
    ],
)
async def test_doc_handler_early_returns(
    update_kwargs: dict[str, Any], context_kwargs: dict[str, Any]
) -> None:
    update_defaults = dict(effective_user=SimpleNamespace(id=1))
    update_defaults.update(update_kwargs)
    update = cast(Update, SimpleNamespace(**update_defaults))
    context_defaults = dict(bot=SimpleNamespace(get_file=AsyncMock()))
    context_defaults.update(context_kwargs)
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(**context_defaults),
    )
    result = await photo_handlers.doc_handler(update, context)
    assert result == photo_handlers.END
