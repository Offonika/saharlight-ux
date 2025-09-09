from types import SimpleNamespace
from typing import Any, cast
from pathlib import Path

import asyncio
import pytest
from openai import OpenAIError
from telegram import PhotoSize, Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.photo_handlers as photo_handlers


class DummyMessage:
    def __init__(self, photo: tuple[PhotoSize, ...] | None = None) -> None:
        self.photo = () if photo is None else photo
        self.replies: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> Any:
        self.replies.append(text)
        # status message returned when text starts with the analysis indicator
        return SimpleNamespace() if text.startswith("🔍") else None


class DummyPhoto:
    file_id = "fid"
    file_unique_id = "uid"


async def _fake_get_file(file_id: str) -> Any:
    class File:
        async def download_as_bytearray(self) -> bytearray:
            return bytearray(b"img")

    return File()


@pytest.mark.asyncio
async def test_photo_handler_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Photo handler returns PHOTO_SUGAR on successful Vision analysis."""
    monkeypatch.chdir(tmp_path)

    async def fake_send_chat_action(*args: Any, **kwargs: Any) -> None:
        pass

    class Run:
        status = "completed"
        thread_id = "tid"
        id = "runid"

    async def fake_send_message(**kwargs: Any) -> Run:
        return Run()

    class DummyClient:
        beta = SimpleNamespace(
            threads=SimpleNamespace(
                runs=SimpleNamespace(retrieve=lambda thread_id, run_id: Run()),
                messages=SimpleNamespace(
                    list=lambda thread_id, run_id: SimpleNamespace(
                        data=[
                            SimpleNamespace(
                                role="assistant",
                                content=[SimpleNamespace(text=SimpleNamespace(value="Суп\nУглеводы: 10 г\nХЕ: 1"))],
                            )
                        ]
                    )
                ),
            )
        )

    msg = DummyMessage(photo=(DummyPhoto(),))
    update = cast(Update, SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            bot=SimpleNamespace(get_file=_fake_get_file, send_chat_action=fake_send_chat_action),
            user_data={"thread_id": "tid"},
        ),
    )
    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)
    monkeypatch.setattr(photo_handlers, "_get_client", lambda: DummyClient())
    monkeypatch.setattr(photo_handlers, "build_main_keyboard", lambda: None)

    result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.PHOTO_SUGAR
    assert any("Суп" in reply for reply in msg.replies)


@pytest.mark.asyncio
async def test_photo_handler_openai_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Photo handler informs user when Vision API fails."""
    monkeypatch.chdir(tmp_path)

    async def fake_send_chat_action(*args: Any, **kwargs: Any) -> None:
        pass

    async def fail_send_message(**kwargs: Any) -> Any:
        raise OpenAIError("boom")

    msg = DummyMessage(photo=(DummyPhoto(),))
    update = cast(Update, SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            bot=SimpleNamespace(get_file=_fake_get_file, send_chat_action=fake_send_chat_action),
            user_data={"thread_id": "tid"},
        ),
    )
    monkeypatch.setattr(photo_handlers, "send_message", fail_send_message)

    result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.END
    assert msg.replies[-1] == "⚠️ Vision не смог обработать фото. Попробуйте ещё раз."
    assert photo_handlers.WAITING_GPT_FLAG not in context.user_data


@pytest.mark.asyncio
async def test_photo_handler_run_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Photo handler informs user when Vision run fails."""
    monkeypatch.chdir(tmp_path)

    async def fake_send_chat_action(*args: Any, **kwargs: Any) -> None:
        pass

    class Run:
        status = "failed"
        thread_id = "tid"
        id = "runid"

    async def fake_send_message(**kwargs: Any) -> Run:
        return Run()

    class DummyStatusMessage:
        def __init__(self) -> None:
            self.edits: list[str] = []

        async def edit_text(self, text: str) -> None:
            self.edits.append(text)

    class DummyMessage:
        def __init__(self) -> None:
            self.photo = (DummyPhoto(),)
            self.replies: list[str] = []
            self.status: DummyStatusMessage | None = None

        async def reply_text(self, text: str, **kwargs: Any) -> Any:
            if text.startswith("🔍"):
                self.status = DummyStatusMessage()
                return self.status
            self.replies.append(text)
            return None

    msg = DummyMessage()
    update = cast(Update, SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            bot=SimpleNamespace(get_file=_fake_get_file, send_chat_action=fake_send_chat_action),
            user_data={"thread_id": "tid"},
        ),
    )
    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)

    result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.END
    assert msg.status is not None
    assert msg.status.edits[-1] == "⚠️ Vision не смог обработать фото. Попробуйте ещё раз."
    assert photo_handlers.WAITING_GPT_FLAG not in context.user_data


@pytest.mark.asyncio
async def test_photo_handler_run_retrieve_openai_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Photo handler informs user when Vision run retrieve fails."""
    monkeypatch.chdir(tmp_path)

    async def fake_send_chat_action(*args: Any, **kwargs: Any) -> None:
        pass

    class Run:
        status = "in_progress"
        thread_id = "tid"
        id = "runid"

    async def fake_send_message(**kwargs: Any) -> Run:
        return Run()

    def fail_retrieve(*args: Any, **kwargs: Any) -> Run:
        raise OpenAIError("boom")

    class DummyClient:
        beta = SimpleNamespace(
            threads=SimpleNamespace(runs=SimpleNamespace(retrieve=fail_retrieve))
        )

    msg = DummyMessage(photo=(DummyPhoto(),))
    update = cast(Update, SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            bot=SimpleNamespace(get_file=_fake_get_file, send_chat_action=fake_send_chat_action),
            user_data={"thread_id": "tid"},
        ),
    )
    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)

    async def fake_sleep(seconds: float) -> None:
        pass

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(photo_handlers, "_get_client", lambda: DummyClient())

    result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.END
    assert msg.replies[-1] == "⚠️ Vision не смог обработать фото. Попробуйте ещё раз."
    assert photo_handlers.WAITING_GPT_FLAG not in context.user_data
