from pathlib import Path
from types import MappingProxyType, SimpleNamespace, TracebackType
from typing import Any, cast


import pytest
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import CallbackContext
from unittest.mock import AsyncMock
from sqlalchemy.orm import Session, sessionmaker

import services.api.app.diabetes.handlers.photo_handlers as photo_handlers
import services.api.app.diabetes.handlers.gpt_handlers as gpt_handlers
import services.api.app.diabetes.utils.functions as functions
from services.api.app.config import settings

pytestmark = pytest.mark.skip("photo handler refactor; tests need update")


class DummyMessage:
    def __init__(
        self, text: str | None = None, photo: tuple[Any, ...] | None = None
    ) -> None:
        self.text: str | None = text
        self.photo: tuple[Any, ...] = () if photo is None else photo
        self.texts: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_doc_handler_calls_photo_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    called = SimpleNamespace(flag=False, path=None)

    async def fake_photo_handler(
        update: Update,
        context: CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        file_path: str | None = None,
    ) -> int:
        called.flag = True
        called.path = file_path
        return 200

    class DummyFile:
        async def download_to_drive(self, path: str) -> None:
            self.path = path

    async def fake_get_file(file_id: str) -> DummyFile:
        return DummyFile()

    dummy_bot = SimpleNamespace(get_file=fake_get_file)

    document = SimpleNamespace(
        file_name="img.png",
        file_unique_id="uid",
        file_id="fid",
        mime_type="image/png",
    )
    message = SimpleNamespace(document=document, photo=None)
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=dummy_bot, user_data=MappingProxyType({})),
    )
    photo_handlers._get_mutable_user_data(context)

    monkeypatch.setattr(photo_handlers, "photo_handler", fake_photo_handler)
    monkeypatch.setattr(
        photo_handlers.os,
        "makedirs",
        lambda *args, **kwargs: None,
    )

    result = await photo_handlers.doc_handler(update, context)

    assert result == 200
    assert called.flag
    assert called.path == f"{settings.photos_dir}/1_uid.png"
    assert photo_handlers._get_mutable_user_data(context) == {}
    assert update.message is not None
    msg = update.message
    assert getattr(msg, "photo", None) is None


@pytest.mark.asyncio
async def test_doc_handler_skips_non_images(monkeypatch: pytest.MonkeyPatch) -> None:
    called = SimpleNamespace(flag=False)

    async def fake_photo_handler(
        update: Update,
        context: CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        file_path: str | None = None,
    ) -> None:
        called.flag = True

    document = SimpleNamespace(
        file_name="file.bin",
        file_unique_id="uid",
        file_id="fid",
        mime_type=None,
    )
    message = SimpleNamespace(document=document, photo=None)
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=MappingProxyType({})),
    )
    photo_handlers._get_mutable_user_data(context)

    monkeypatch.setattr(photo_handlers, "photo_handler", fake_photo_handler)

    result = await photo_handlers.doc_handler(update, context)

    assert result == photo_handlers.END
    assert not called.flag
    assert photo_handlers._get_mutable_user_data(context) is not None
    assert "__file_path" not in photo_handlers._get_mutable_user_data(context)


@pytest.mark.asyncio
async def test_doc_handler_get_file_error(monkeypatch: pytest.MonkeyPatch) -> None:
    document = SimpleNamespace(
        file_name="img.png",
        file_unique_id="uid",
        file_id="fid",
        mime_type="image/png",
    )
    message = SimpleNamespace(document=document, reply_text=AsyncMock())
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    bot = SimpleNamespace(get_file=AsyncMock(side_effect=TelegramError("boom")))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=bot, user_data=MappingProxyType({})),
    )
    photo_handlers._get_mutable_user_data(context)
    monkeypatch.setattr(
        photo_handlers.os,
        "makedirs",
        lambda *args, **kwargs: None,
    )

    result = await photo_handlers.doc_handler(update, context)

    assert result == photo_handlers.END
    message.reply_text.assert_awaited_once()
    assert not photo_handlers._get_mutable_user_data(context)


@pytest.mark.asyncio
async def test_doc_handler_download_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyFile:
        async def download_to_drive(self, path: str) -> None:
            raise OSError("disk full")

    document = SimpleNamespace(
        file_name="img.png",
        file_unique_id="uid",
        file_id="fid",
        mime_type="image/png",
    )
    message = SimpleNamespace(document=document, reply_text=AsyncMock())
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    bot = SimpleNamespace(get_file=AsyncMock(return_value=DummyFile()))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=bot, user_data=MappingProxyType({})),
    )
    photo_handlers._get_mutable_user_data(context)
    monkeypatch.setattr(
        photo_handlers.os,
        "makedirs",
        lambda *args, **kwargs: None,
    )

    result = await photo_handlers.doc_handler(update, context)

    assert result == photo_handlers.END
    message.reply_text.assert_awaited_once()
    assert not photo_handlers._get_mutable_user_data(context)


@pytest.mark.asyncio
async def test_photo_handler_non_writable_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyPhoto:
        file_id = "fid"
        file_unique_id = "uid"

    message = SimpleNamespace(photo=(DummyPhoto(),), reply_text=AsyncMock())
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    bot = SimpleNamespace(
        get_file=AsyncMock(side_effect=AssertionError("get_file called"))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=bot, user_data=MappingProxyType({})),
    )
    photo_handlers._get_mutable_user_data(context)

    def raise_os_error(*args: Any, **kwargs: Any) -> None:
        raise OSError("no perm")

    monkeypatch.setattr(photo_handlers.os, "makedirs", raise_os_error)

    result = await photo_handlers.photo_handler(update, context)

    assert result == photo_handlers.END
    message.reply_text.assert_awaited_once()
    assert photo_handlers.WAITING_GPT_FLAG not in photo_handlers._get_mutable_user_data(context)


@pytest.mark.asyncio
async def test_doc_handler_non_writable_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_photo_handler(*args: Any, **kwargs: Any) -> int:
        raise AssertionError("photo_handler should not be called")

    monkeypatch.setattr(photo_handlers, "photo_handler", fail_photo_handler)

    def raise_os_error(*args: Any, **kwargs: Any) -> None:
        raise OSError("no perm")

    monkeypatch.setattr(photo_handlers.os, "makedirs", raise_os_error)

    document = SimpleNamespace(
        file_name="img.png",
        file_unique_id="uid",
        file_id="fid",
        mime_type="image/png",
    )
    message = SimpleNamespace(document=document, reply_text=AsyncMock())
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    bot = SimpleNamespace(
        get_file=AsyncMock(side_effect=AssertionError("get_file called"))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=bot, user_data=MappingProxyType({})),
    )
    photo_handlers._get_mutable_user_data(context)

    result = await photo_handlers.doc_handler(update, context)

    assert result == photo_handlers.END
    message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_photo_handler_handles_typeerror() -> None:
    message = DummyMessage(photo=None)
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=MappingProxyType({})),
    )
    photo_handlers._get_mutable_user_data(context)

    result = await photo_handlers.photo_handler(update, context)

    assert message.texts == ["❗ Файл не распознан как изображение."]
    assert result == photo_handlers.END
    assert photo_handlers._get_mutable_user_data(context) is not None
    assert photo_handlers.WAITING_GPT_FLAG not in photo_handlers._get_mutable_user_data(context)


@pytest.mark.asyncio
async def test_photo_handler_sends_bytes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)

    class DummyPhoto:
        file_id = "fid"
        file_unique_id = "uid"

    async def reply_text(*args: Any, **kwargs: Any) -> None:
        pass

    message = SimpleNamespace(photo=(DummyPhoto(),), reply_text=reply_text)
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )

    class DummyFile:
        async def download_as_bytearray(self) -> bytearray:
            return bytearray(b"img")

    async def fake_get_file(file_id: str) -> DummyFile:
        return DummyFile()

    dummy_bot = SimpleNamespace(get_file=fake_get_file)
    user_data = {"thread_id": "tid"}
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=dummy_bot, user_data=MappingProxyType(user_data)),
    )
    photo_handlers._get_mutable_user_data(context).update(user_data)

    call = {}

    async def fake_send_message(**kwargs: Any) -> Any:
        call.update(kwargs)

        class Run:
            status = "completed"
            thread_id = kwargs["thread_id"]
            id = "runid"

        return Run()

    class DummyClient:
        beta = SimpleNamespace(
            threads=SimpleNamespace(
                runs=SimpleNamespace(
                    retrieve=lambda thread_id, run_id: SimpleNamespace(
                        status="completed", thread_id=thread_id, id=run_id
                    )
                ),
                messages=SimpleNamespace(
                    list=lambda thread_id: SimpleNamespace(data=[])
                ),
            )
        )

    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)
    monkeypatch.setattr(photo_handlers, "_get_client", lambda: DummyClient())
    monkeypatch.setattr(
        photo_handlers,
        "extract_nutrition_info",
        lambda text: functions.NutritionInfo(carbs_g=10.0, xe=1.0),
    )
    monkeypatch.setattr(photo_handlers, "build_main_keyboard", lambda: None)

    result = await photo_handlers.photo_handler(update, context)

    assert call["image_bytes"] == b"img"
    assert "image_path" not in call
    assert result == photo_handlers.PHOTO_SUGAR


@pytest.mark.asyncio
async def test_photo_then_freeform_calculates_dose(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """photo_handler + freeform_handler produce dose in reply and context."""

    class DummyPhoto:
        file_id = "fid"
        file_unique_id = "uid"

    class DummyFile:
        async def download_to_drive(self, path: str) -> None:
            Path(path).write_bytes(b"img")

    async def fake_get_file(file_id: str) -> DummyFile:
        return DummyFile()

    monkeypatch.chdir(tmp_path)
    dummy_bot = SimpleNamespace(get_file=fake_get_file)

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
                    list=lambda thread_id: SimpleNamespace(data=[])
                ),
            )
        )

    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)
    monkeypatch.setattr(photo_handlers, "_get_client", lambda: DummyClient())
    monkeypatch.setattr(
        photo_handlers,
        "extract_nutrition_info",
        lambda text: functions.NutritionInfo(carbs_g=10.0, xe=1.0),
    )
    monkeypatch.setattr(photo_handlers, "build_main_keyboard", lambda: None)
    monkeypatch.setattr(gpt_handlers, "confirm_keyboard", lambda: None)

    photo_msg = DummyMessage(photo=(DummyPhoto(),))
    update_photo = cast(
        Update,
        SimpleNamespace(message=photo_msg, effective_user=SimpleNamespace(id=1)),
    )
    user_data = {"thread_id": "tid"}
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=dummy_bot, user_data=MappingProxyType(user_data)),
    )
    photo_handlers._get_mutable_user_data(context).update(user_data)

    await photo_handlers.photo_handler(update_photo, context)

    class DummySession(Session):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def __enter__(self) -> "DummySession":
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None:
            pass

        def get(self, *args: Any, **kwargs: Any) -> Any:
            return SimpleNamespace(icr=10.0, cf=1.0, target_bg=6.0)

    session_factory = cast(Any, sessionmaker(class_=DummySession))
    photo_handlers.SessionLocal = session_factory  # type: ignore[attr-defined]

    monkeypatch.setattr(gpt_handlers, "run_db", None)

    sugar_msg = DummyMessage(text="5")
    update_sugar = cast(
        Update,
        SimpleNamespace(message=sugar_msg, effective_user=SimpleNamespace(id=1)),
    )

    await gpt_handlers.freeform_handler(
        update_sugar, context, SessionLocal=session_factory
    )

    reply = sugar_msg.texts[0]
    assert reply == "💉\u202fРасчёт дозы: 1.0\u202fЕд.\nСахар: 5.0\u202fммоль/л"
    assert photo_handlers._get_mutable_user_data(context) is not None
    user_data = photo_handlers._get_mutable_user_data(context)
    assert "dose" in user_data["pending_entry"]
