from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from telegram import Update
from telegram.ext import CallbackContext

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401

import services.api.app.diabetes.handlers.photo_handlers as photo_handlers


class DummyPhoto:
    file_id = "fid"
    file_unique_id = "uid"


@pytest.mark.asyncio
async def test_photo_handler_commit_failure(
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
            async def download_to_drive(self, path: str) -> None:
                Path(path).write_bytes(b"img")

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

    async def fake_create_thread() -> str:
        return "tid"

    send_message_mock = AsyncMock()

    monkeypatch.setattr(photo_handlers, "SessionLocal", lambda: DummySession())
    monkeypatch.setattr(photo_handlers, "create_thread", fake_create_thread)
    monkeypatch.setattr(photo_handlers, "commit", lambda session: False)
    monkeypatch.setattr(photo_handlers, "send_message", send_message_mock)

    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=SimpleNamespace(get_file=fake_get_file), user_data={}),
    )

    monkeypatch.chdir(tmp_path)
    result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.END
    assert message.texts == ["⚠️ Не удалось сохранить данные пользователя."]
    user_data = context.user_data
    assert user_data is not None
    assert photo_handlers.WAITING_GPT_FLAG not in user_data
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
            async def download_to_drive(self, path: str) -> None:
                Path(path).write_bytes(b"img")

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
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            bot=SimpleNamespace(get_file=fake_get_file), user_data={"thread_id": "tid"}
        ),
    )

    monkeypatch.chdir(tmp_path)
    result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.END
    assert message.status is not None
    assert message.status.edits == ["⚠️ Vision не смог обработать фото."]
    user_data = context.user_data
    assert user_data is not None
    assert photo_handlers.WAITING_GPT_FLAG not in user_data


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
            async def download_to_drive(self, path: str) -> None:
                Path(path).write_bytes(b"img")

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
            threads=SimpleNamespace(messages=SimpleNamespace(list=lambda thread_id: Messages()))
        )

    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)
    monkeypatch.setattr(photo_handlers, "_get_client", lambda: DummyClient())
    monkeypatch.setattr(photo_handlers, "extract_nutrition_info", lambda t: (None, None))

    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            bot=SimpleNamespace(get_file=fake_get_file), user_data={"thread_id": "tid"}
        ),
    )

    monkeypatch.chdir(tmp_path)
    result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.END
    assert any("Не смог разобрать" in t for t in message.texts)
    user_data = context.user_data
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
        SimpleNamespace(bot=bot, user_data={}),
    )
    photo_mock = AsyncMock()
    monkeypatch.setattr(photo_handlers, "photo_handler", photo_mock)

    result = await photo_handlers.doc_handler(update, context)

    assert result == photo_handlers.END
    assert not photo_mock.called
    assert not bot.get_file.called
