from pathlib import Path
from types import SimpleNamespace, TracebackType
from typing import Any, Callable, TypeVar, cast


import pytest
from telegram import Update
from telegram.ext import CallbackContext
from sqlalchemy.orm import Session, sessionmaker

import services.api.app.diabetes.handlers.photo_handlers as photo_handlers
import services.api.app.diabetes.handlers.gpt_handlers as gpt_handlers


T = TypeVar("T")


class DummyMessage:
    def __init__(self, text: str | None = None, photo: tuple[Any, ...] | None = None) -> None:
        self.text: str | None = text
        self.photo: tuple[Any, ...] = () if photo is None else photo
        self.texts: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_doc_handler_calls_photo_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    called = SimpleNamespace(flag=False)

    async def fake_photo_handler(
        update: Update,
        context: CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
    ) -> int:
        called.flag = True
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
    update = cast(Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=dummy_bot, user_data={}),
    )

    monkeypatch.setattr(photo_handlers, "photo_handler", fake_photo_handler)
    monkeypatch.setattr(photo_handlers.os, "makedirs", lambda *args, **kwargs: None)

    result = await photo_handlers.doc_handler(update, context)

    assert result == 200
    assert called.flag
    assert context.user_data is not None
    user_data = context.user_data
    assert user_data["__file_path"] == "photos/1_uid.png"
    assert update.message is not None
    msg = update.message
    assert msg.photo == ()


@pytest.mark.asyncio
async def test_doc_handler_skips_non_images(monkeypatch: pytest.MonkeyPatch) -> None:
    called = SimpleNamespace(flag=False)

    async def fake_photo_handler(
        update: Update,
        context: CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
    ) -> None:
        called.flag = True

    document = SimpleNamespace(
        file_name="file.bin",
        file_unique_id="uid",
        file_id="fid",
        mime_type=None,
    )
    message = SimpleNamespace(document=document, photo=None)
    update = cast(Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )

    monkeypatch.setattr(photo_handlers, "photo_handler", fake_photo_handler)

    result = await photo_handlers.doc_handler(update, context)

    assert result == photo_handlers.ConversationHandler.END
    assert not called.flag
    assert context.user_data is not None
    assert "__file_path" not in context.user_data


@pytest.mark.asyncio
async def test_photo_handler_handles_typeerror() -> None:
    message = DummyMessage(photo=None)
    update = cast(Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )

    result = await photo_handlers.photo_handler(update, context)

    assert message.texts == ["❗ Файл не распознан как изображение."]
    assert result == photo_handlers.ConversationHandler.END
    assert context.user_data is not None
    assert photo_handlers.WAITING_GPT_FLAG not in context.user_data


@pytest.mark.asyncio
async def test_photo_handler_removes_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    class DummyPhoto:
        file_id = "fid"
        file_unique_id = "uid"

    async def reply_text(*args: Any, **kwargs: Any) -> None:
        pass

    message = SimpleNamespace(photo=(DummyPhoto(),), reply_text=reply_text)
    update = cast(Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)))

    class DummyFile:
        async def download_to_drive(self, path: str) -> None:
            Path(path).write_bytes(b"img")

    async def fake_get_file(file_id: str) -> DummyFile:
        return DummyFile()

    dummy_bot = SimpleNamespace(get_file=fake_get_file)
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=dummy_bot, user_data={"thread_id": "tid"}),
    )

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
                messages=SimpleNamespace(list=lambda thread_id: SimpleNamespace(data=[])),
            )
        )

    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)
    monkeypatch.setattr(photo_handlers, "_get_client", lambda: DummyClient())
    monkeypatch.setattr(photo_handlers, "extract_nutrition_info", lambda text: (10.0, 1.0))
    monkeypatch.setattr(photo_handlers, "menu_keyboard", None)
    monkeypatch.setattr(
        photo_handlers.os,
        "makedirs",
        lambda path, **kwargs: Path(path).mkdir(parents=True, exist_ok=True),
    )

    result = await photo_handlers.photo_handler(update, context)

    assert call["keep_image"] is True
    assert not Path(call["image_path"]).exists()
    assert result == photo_handlers.PHOTO_SUGAR


@pytest.mark.asyncio
async def test_photo_then_freeform_calculates_dose(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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
                messages=SimpleNamespace(list=lambda thread_id: SimpleNamespace(data=[])),
            )
        )

    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)
    monkeypatch.setattr(photo_handlers, "_get_client", lambda: DummyClient())
    monkeypatch.setattr(photo_handlers, "extract_nutrition_info", lambda text: (10.0, 1.0))
    monkeypatch.setattr(photo_handlers, "menu_keyboard", None)
    monkeypatch.setattr(gpt_handlers, "confirm_keyboard", lambda: None)

    photo_msg = DummyMessage(photo=(DummyPhoto(),))
    update_photo = cast(
        Update,
        SimpleNamespace(message=photo_msg, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=dummy_bot, user_data={"thread_id": "tid"}),
    )

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
    photo_handlers.SessionLocal = session_factory
    gpt_handlers.SessionLocal = session_factory

    async def fake_run_db(
        func: Callable[[Session], T],
        *args: Any,
        sessionmaker: Callable[[], Session],
        **kwargs: Any,
    ) -> T:
        with cast(Any, sessionmaker()) as s:
            return func(cast(Session, s), *args, **kwargs)

    monkeypatch.setattr(gpt_handlers, "run_db", fake_run_db)

    sugar_msg = DummyMessage(text="5")
    update_sugar = cast(
        Update,
        SimpleNamespace(message=sugar_msg, effective_user=SimpleNamespace(id=1)),
    )

    await gpt_handlers.freeform_handler(update_sugar, context)

    reply = sugar_msg.texts[0]
    assert reply == "💉\u202fРасчёт дозы: 1.0\u202fЕд.\nСахар: 5.0\u202fммоль/л"
    assert context.user_data is not None
    user_data = context.user_data
    assert "dose" in user_data["pending_entry"]
