from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from telegram import Update
from telegram.ext import CallbackContext

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")

import services.api.app.diabetes.handlers.photo_handlers as photo_handlers
import services.api.app.diabetes.utils.functions as functions


class DummyPhoto:
    file_id = "fid"
    file_unique_id = "uid"


@pytest.mark.asyncio
async def test_photo_handler_commit_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
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

    class DummySession:
        def __enter__(self) -> "DummySession":
            return self

        def __exit__(self, *args: Any) -> None:
            pass

        def get(self, *args: Any, **kwargs: Any) -> Any:
            return None

        def add(self, obj: Any) -> None:
            pass

    def fake_create_thread_sync() -> str:
        return "tid"

    send_message_mock = AsyncMock()

    monkeypatch.setattr(photo_handlers, "SessionLocal", lambda: DummySession())
    monkeypatch.setattr(photo_handlers, "create_thread_sync", fake_create_thread_sync)

    def fail_commit(session: object) -> None:
        raise photo_handlers.CommitError

    monkeypatch.setattr(photo_handlers, "commit", fail_commit)
    monkeypatch.setattr(photo_handlers, "send_message", send_message_mock)

    async def run_db_stub(fn, *args, sessionmaker, **kwargs) -> Any:
        def wrapper() -> Any:
            with sessionmaker() as sess:
                return fn(sess, *args, **kwargs)

        return await asyncio.to_thread(wrapper)

    monkeypatch.setattr(photo_handlers, "run_db", run_db_stub)

    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            bot=SimpleNamespace(get_file=fake_get_file),
            user_data=MappingProxyType({}),
        ),
    )

    monkeypatch.chdir(tmp_path)
    with caplog.at_level(logging.ERROR):
        result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.END
    assert message.texts == ["⚠️ Не удалось сохранить данные пользователя."]
    user_data = photo_handlers._get_mutable_user_data(context)
    assert user_data is not None
    assert photo_handlers.WAITING_GPT_FLAG not in user_data
    assert not send_message_mock.called
    assert any(
        "[PHOTO] Failed to commit user 1" in r.getMessage() for r in caplog.records
    )


@pytest.mark.asyncio
async def test_photo_handler_commit_failure_resets_waiting_flag(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
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

    class DummySession:
        def __enter__(self) -> "DummySession":
            return self

        def __exit__(self, *args: Any) -> None:
            pass

        def get(self, *args: Any, **kwargs: Any) -> Any:
            return None

        def add(self, obj: Any) -> None:
            pass

    def fake_create_thread_sync() -> str:
        return "tid"

    def fail_commit(session: object) -> None:
        raise photo_handlers.CommitError

    send_message_mock = AsyncMock()

    monkeypatch.setattr(photo_handlers, "SessionLocal", lambda: DummySession())
    monkeypatch.setattr(photo_handlers, "create_thread_sync", fake_create_thread_sync)
    monkeypatch.setattr(photo_handlers, "commit", fail_commit)
    monkeypatch.setattr(photo_handlers, "send_message", send_message_mock)

    async def run_db_stub(fn, *args, sessionmaker, **kwargs) -> Any:
        def wrapper() -> Any:
            with sessionmaker() as sess:
                return fn(sess, *args, **kwargs)

        return await asyncio.to_thread(wrapper)

    monkeypatch.setattr(photo_handlers, "run_db", run_db_stub)

    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            bot=SimpleNamespace(get_file=fake_get_file),
            user_data=MappingProxyType({}),
        ),
    )

    monkeypatch.chdir(tmp_path)
    result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.END
    user_data = photo_handlers._get_mutable_user_data(context)
    assert user_data is not None
    assert photo_handlers.WAITING_GPT_FLAG not in user_data
    assert photo_handlers.WAITING_GPT_TIMESTAMP not in user_data
    assert not send_message_mock.called


@pytest.mark.asyncio
async def test_photo_handler_run_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class StatusMessage:
        def __init__(self) -> None:
            self.edits: list[str] = []

        async def edit_text(self, text: str, **kwargs: Any) -> None:
            self.edits.append(text)

    class DummyMessage:
        def __init__(self) -> None:
            self.photo = (DummyPhoto(),)
            self.texts: list[str] = []
            self.status: StatusMessage | None = None

        async def reply_text(self, text: str, **kwargs: Any) -> StatusMessage | None:
            self.texts.append(text)
            if text.startswith("🔍"):
                self.status = StatusMessage()
                return self.status
            return None

    async def fake_get_file(file_id: str) -> Any:
        class File:
            async def download_as_bytearray(self) -> bytearray:
                return bytearray(b"img")

        return File()

    class Run:
        status = "failed"
        thread_id = "tid"
        id = "rid"

    async def fake_send_message(**kwargs: Any) -> Run:
        return Run()

    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)

    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    user_data = {"thread_id": "tid"}
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            bot=SimpleNamespace(get_file=fake_get_file),
            user_data=MappingProxyType(user_data),
        ),
    )

    monkeypatch.chdir(tmp_path)
    result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.END
    assert message.status is not None
    assert message.status.edits == [
        "⚠️ Vision не смог обработать фото. Попробуйте ещё раз."
    ]
    user_data = photo_handlers._get_mutable_user_data(context)
    assert user_data is not None
    assert photo_handlers.WAITING_GPT_FLAG not in user_data


@pytest.mark.asyncio
async def test_photo_handler_run_retrieve_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class StatusMessage:
        def __init__(self) -> None:
            self.delete = AsyncMock()

    class DummyMessage:
        def __init__(self) -> None:
            self.photo = (DummyPhoto(),)
            self.texts: list[str] = []
            self.status = StatusMessage()

        async def reply_text(self, text: str, **kwargs: Any) -> StatusMessage | None:
            self.texts.append(text)
            if text.startswith("🔍"):
                return self.status
            return None

    async def fake_get_file(file_id: str) -> Any:
        class File:
            async def download_as_bytearray(self) -> bytearray:
                return bytearray(b"img")

        return File()

    class Run:
        status = "in_progress"
        thread_id = "tid"
        id = "rid"

    async def fake_send_message(**kwargs: Any) -> Run:
        return Run()

    def timeout_retrieve(*args: Any, **kwargs: Any) -> None:
        raise asyncio.TimeoutError

    dummy_client = SimpleNamespace(
        beta=SimpleNamespace(
            threads=SimpleNamespace(runs=SimpleNamespace(retrieve=timeout_retrieve))
        )
    )

    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)
    monkeypatch.setattr(photo_handlers, "_get_client", lambda: dummy_client)
    monkeypatch.setattr(photo_handlers.asyncio, "sleep", AsyncMock())

    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    user_data = {"thread_id": "tid"}
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            bot=SimpleNamespace(get_file=fake_get_file),
            user_data=MappingProxyType(user_data),
        ),
    )

    monkeypatch.chdir(tmp_path)
    result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.END
    assert message.texts[-1] == "⚠️ Превышено время ожидания Vision. Попробуйте ещё раз."
    assert message.status.delete.called
    user_data = photo_handlers._get_mutable_user_data(context)
    assert user_data is not None
    assert photo_handlers.WAITING_GPT_FLAG not in user_data
    assert photo_handlers.WAITING_GPT_TIMESTAMP not in user_data


@pytest.mark.asyncio
async def test_photo_handler_unparsed_response(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class DummyMessage:
        def __init__(self) -> None:
            self.photo = (DummyPhoto(),)
            self.texts: list[str] = []

        async def reply_text(self, text: str, **kwargs: Any) -> Any:
            self.texts.append(text)
            if text.startswith("🔍"):
                return SimpleNamespace()
            return None

    async def fake_get_file(file_id: str) -> Any:
        class File:
            async def download_as_bytearray(self) -> bytearray:
                return bytearray(b"img")

        return File()

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

    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)
    monkeypatch.setattr(photo_handlers, "_get_client", lambda: DummyClient())
    monkeypatch.setattr(
        photo_handlers,
        "extract_nutrition_info",
        lambda t: functions.NutritionInfo(),
    )

    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    user_data = {"thread_id": "tid"}
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            bot=SimpleNamespace(get_file=fake_get_file),
            user_data=MappingProxyType(user_data),
        ),
    )

    monkeypatch.chdir(tmp_path)
    result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.END
    assert any("Не смог разобрать" in t for t in message.texts)
    user_data = photo_handlers._get_mutable_user_data(context)
    assert user_data is not None
    assert "pending_entry" not in user_data
    assert photo_handlers.WAITING_GPT_FLAG not in user_data


@pytest.mark.asyncio
async def test_photo_handler_unparsed_response_clears_pending_entry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class DummyMessage:
        def __init__(self) -> None:
            self.photo = (DummyPhoto(),)
            self.texts: list[str] = []

        async def reply_text(self, text: str, **kwargs: Any) -> Any:
            self.texts.append(text)
            if text.startswith("🔍"):
                return SimpleNamespace()
            return None

    async def fake_get_file(file_id: str) -> Any:
        class File:
            async def download_as_bytearray(self) -> bytearray:
                return bytearray(b"img")

        return File()

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

    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)
    monkeypatch.setattr(photo_handlers, "_get_client", lambda: DummyClient())
    monkeypatch.setattr(
        photo_handlers,
        "extract_nutrition_info",
        lambda t: functions.NutritionInfo(),
    )

    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            bot=SimpleNamespace(get_file=fake_get_file),
            user_data={"thread_id": "tid", "pending_entry": {"foo": "bar"}},
        ),
    )

    monkeypatch.chdir(tmp_path)
    result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.END
    assert any("Не смог разобрать" in t for t in message.texts)
    user_data = photo_handlers._get_mutable_user_data(context)
    assert user_data is not None
    assert "pending_entry" not in user_data
    assert photo_handlers.WAITING_GPT_FLAG not in user_data


@pytest.mark.asyncio
@pytest.mark.parametrize("mime", [None, "text/plain"])
async def test_doc_handler_rejects_non_image(
    monkeypatch: pytest.MonkeyPatch, mime: str | None
) -> None:
    document = SimpleNamespace(
        mime_type=mime,
        file_name="f.txt",
        file_unique_id="uid",
        file_id="fid",
    )
    message = SimpleNamespace(document=document)
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    bot = SimpleNamespace(get_file=AsyncMock())
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=bot, user_data=MappingProxyType({})),
    )
    photo_handlers._get_mutable_user_data(context)
    photo_mock = AsyncMock()
    monkeypatch.setattr(photo_handlers, "photo_handler", photo_mock)

    result = await photo_handlers.doc_handler(update, context)

    assert result == photo_handlers.END
    assert not photo_mock.called
    assert not bot.get_file.called


@pytest.mark.asyncio
async def test_photo_handler_long_vision_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    long_text = "x" * (photo_handlers.MessageLimit.MAX_TEXT_LENGTH + 100)

    class DummyMessage:
        def __init__(self) -> None:
            self.photo = (DummyPhoto(),)
            self.texts: list[str] = []
            self.docs: list[Any] = []
            self.status = SimpleNamespace(delete=AsyncMock())

        async def reply_text(self, text: str, **kwargs: Any) -> Any:
            self.texts.append(text)
            if text.startswith("🔍"):
                return self.status
            return None

        async def reply_document(self, document: Any, **kwargs: Any) -> None:
            self.docs.append(document)

    class File:
        async def download_as_bytearray(self) -> bytearray:
            return bytearray(b"img")

    bot = SimpleNamespace(
        get_file=AsyncMock(return_value=File()),
        send_chat_action=AsyncMock(),
    )

    def fake_create_thread_sync() -> str:
        return "tid"

    class DummySession:
        def __enter__(self) -> "DummySession":
            return self

        def __exit__(self, *args: Any) -> None:
            pass

        def get(self, *args: Any, **kwargs: Any) -> Any:
            return None

        def add(self, obj: Any) -> None:
            pass

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
                content=[SimpleNamespace(text=SimpleNamespace(value=long_text))],
            )
        ]

    class DummyClient:
        beta = SimpleNamespace(
            threads=SimpleNamespace(
                messages=SimpleNamespace(list=lambda thread_id: Messages())
            )
        )

    monkeypatch.setattr(photo_handlers, "SessionLocal", lambda: DummySession())
    monkeypatch.setattr(photo_handlers, "create_thread_sync", fake_create_thread_sync)
    monkeypatch.setattr(photo_handlers, "commit", lambda s: None)
    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)
    monkeypatch.setattr(photo_handlers, "_get_client", lambda: DummyClient())
    monkeypatch.setattr(
        photo_handlers,
        "extract_nutrition_info",
        lambda text: functions.NutritionInfo(carbs_g=10, xe=1),
    )
    monkeypatch.setattr(photo_handlers, "build_main_keyboard", lambda: None)

    async def run_db_stub(fn, *args, sessionmaker, **kwargs) -> Any:
        def wrapper() -> Any:
            with sessionmaker() as sess:
                return fn(sess, *args, **kwargs)

        return await asyncio.to_thread(wrapper)

    monkeypatch.setattr(photo_handlers, "run_db", run_db_stub)

    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=bot, user_data=MappingProxyType({})),
    )
    photo_handlers._get_mutable_user_data(context)

    monkeypatch.chdir(tmp_path)
    result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.PHOTO_SUGAR
    assert message.docs
    assert any("слишком длинный" in t for t in message.texts)
    assert long_text not in message.texts[-1]


@pytest.mark.asyncio
async def test_photo_handler_long_vision_text_parse_fail(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    long_text = "y" * (photo_handlers.MessageLimit.MAX_TEXT_LENGTH + 100)

    class DummyMessage:
        def __init__(self) -> None:
            self.photo = (DummyPhoto(),)
            self.texts: list[str] = []
            self.kwargs: list[dict[str, Any]] = []
            self.docs: list[Any] = []
            self.status = SimpleNamespace(delete=AsyncMock())

        async def reply_text(self, text: str, **kwargs: Any) -> Any:
            self.texts.append(text)
            self.kwargs.append(kwargs)
            if text.startswith("🔍"):
                return self.status
            return None

        async def reply_document(self, document: Any, **kwargs: Any) -> None:
            self.docs.append(document)

    class File:
        async def download_as_bytearray(self) -> bytearray:
            return bytearray(b"img")

    bot = SimpleNamespace(
        get_file=AsyncMock(return_value=File()),
        send_chat_action=AsyncMock(),
    )

    def fake_create_thread_sync() -> str:
        return "tid"

    class DummySession:
        def __enter__(self) -> "DummySession":
            return self

        def __exit__(self, *args: Any) -> None:
            pass

        def get(self, *args: Any, **kwargs: Any) -> Any:
            return None

        def add(self, obj: Any) -> None:
            pass

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
                content=[SimpleNamespace(text=SimpleNamespace(value=long_text))],
            )
        ]

    class DummyClient:
        beta = SimpleNamespace(
            threads=SimpleNamespace(
                messages=SimpleNamespace(list=lambda thread_id: Messages())
            )
        )

    monkeypatch.setattr(photo_handlers, "SessionLocal", lambda: DummySession())
    monkeypatch.setattr(photo_handlers, "create_thread_sync", fake_create_thread_sync)
    monkeypatch.setattr(photo_handlers, "commit", lambda s: None)
    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)
    monkeypatch.setattr(photo_handlers, "_get_client", lambda: DummyClient())
    monkeypatch.setattr(
        photo_handlers,
        "extract_nutrition_info",
        lambda text: functions.NutritionInfo(),
    )
    monkeypatch.setattr(photo_handlers, "build_main_keyboard", lambda: None)

    async def run_db_stub(fn, *args, sessionmaker, **kwargs) -> Any:
        def wrapper() -> Any:
            with sessionmaker() as sess:
                return fn(sess, *args, **kwargs)

        return await asyncio.to_thread(wrapper)

    monkeypatch.setattr(photo_handlers, "run_db", run_db_stub)

    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=bot, user_data=MappingProxyType({})),
    )
    photo_handlers._get_mutable_user_data(context)

    monkeypatch.chdir(tmp_path)
    result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.END
    assert message.docs
    assert any("слишком длинный" in t for t in message.texts)
    assert message.kwargs[-1].get("parse_mode") is None
