from pathlib import Path
from types import SimpleNamespace, TracebackType
from typing import Any, Callable, TypeVar, cast

from unittest.mock import Mock, PropertyMock

import pytest
from telegram import PhotoSize, Update
from telegram.ext import CallbackContext
from sqlalchemy.orm import Session, sessionmaker

import services.api.app.diabetes.handlers.photo_handlers as photo_handlers
import services.api.app.diabetes.handlers.gpt_handlers as gpt_handlers
import services.api.app.diabetes.handlers.router as router


T = TypeVar("T")


class DummyMessage:
    def __init__(self, text: str | None = None, photo: tuple[PhotoSize, ...] | None = None) -> None:
        self.text: str | None = text
        self.photo: tuple[PhotoSize, ...] = () if photo is None else photo
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


class DummyQuery:
    def __init__(self, message: DummyMessage, data: str) -> None:
        self.data = data
        self.message = message
        self.edited: list[str] = []

    async def answer(self) -> None:
        pass

    async def edit_message_text(self, text: str, **kwargs: Any) -> None:
        self.edited.append(text)


class DummyPhoto:
    file_id = "fid"
    file_unique_id = "uid"


class DummySession(Session):
    added_entries: list[Any] = []

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

    def add(self, instance: object, _warn: bool = False) -> None:
        DummySession.added_entries.append(instance)

    def commit(self) -> None:
        pass

    def get(self, *args: Any, **kwargs: Any) -> Any:
        return SimpleNamespace(icr=10.0, cf=1.0, target_bg=6.0)

    def close(self) -> None:
        pass


@pytest.mark.asyncio
async def test_photo_flow_saves_entry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    async def fake_parse_command(text: str) -> dict[str, Any]:
        return {"action": "add_entry", "fields": {}, "entry_date": None, "time": None}

    monkeypatch.setattr(gpt_handlers, "parse_command", fake_parse_command)
    monkeypatch.setattr(gpt_handlers, "confirm_keyboard", lambda: None)
    monkeypatch.setattr(gpt_handlers, "menu_keyboard", None)
    monkeypatch.setattr(photo_handlers, "menu_keyboard", None)

    msg_start = DummyMessage("/dose")
    update_start = cast(
        Update,
        SimpleNamespace(message=msg_start, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        Mock(spec=CallbackContext),
    )
    user_data_ref: dict[str, Any] = {}
    setattr(cast(Any, type(context)), "user_data", PropertyMock(return_value=user_data_ref))
    setattr(cast(Any, type(context)), "job_queue", PropertyMock(return_value=None))

    assert context.user_data is not None
    user_data = context.user_data

    async def fake_get_file(file_id: str) -> Any:
        class File:
            async def download_to_drive(self, path: str) -> None:
                Path(path).write_bytes(b"img")

        return File()

    fake_bot = SimpleNamespace(get_file=fake_get_file)
    setattr(cast(Any, type(context)), "bot", PropertyMock(return_value=fake_bot))

    await gpt_handlers.freeform_handler(update_start, context)

    monkeypatch.chdir(tmp_path)

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
                    list=lambda thread_id: SimpleNamespace(
                        data=[
                            SimpleNamespace(
                                role="assistant",
                                content=[SimpleNamespace(text=SimpleNamespace(value="carbs 30g xe 2"))],
                            )
                        ]
                    )
                ),
            )
        )

    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)
    monkeypatch.setattr(photo_handlers, "_get_client", lambda: DummyClient())
    monkeypatch.setattr(photo_handlers, "extract_nutrition_info", lambda text: (30.0, 2.0))
    user_data["thread_id"] = "tid"

    msg_photo = DummyMessage(photo=cast(tuple[PhotoSize, ...], (DummyPhoto(),)))
    update_photo = cast(
        Update,
        SimpleNamespace(message=msg_photo, effective_user=SimpleNamespace(id=1)),
    )
    await photo_handlers.photo_handler(update_photo, context)

    entry = user_data["pending_entry"]
    assert entry["carbs_g"] == 30.0
    assert entry["xe"] == 2.0
    assert entry["photo_path"].endswith("uid.jpg")

    msg_sugar = DummyMessage("5.5")
    update_sugar = cast(
        Update,
        SimpleNamespace(message=msg_sugar, effective_user=SimpleNamespace(id=1)),
    )
    session_factory = cast(Any, sessionmaker(class_=DummySession))
    photo_handlers.SessionLocal = session_factory
    gpt_handlers.SessionLocal = session_factory

    async def fake_run_db(
        func: Callable[..., T],
        *args: Any,
        sessionmaker: Callable[[], Session],
        **kwargs: Any,
    ) -> T:
        session = sessionmaker()
        try:
            return func(session, *args, **kwargs)
        finally:
            session.close()

    monkeypatch.setattr(gpt_handlers, "run_db", fake_run_db)
    await gpt_handlers.freeform_handler(update_sugar, context)
    assert user_data["pending_entry"]["sugar_before"] == 5.5

    monkeypatch.setattr(router, "SessionLocal", session_factory)
    import services.api.app.diabetes.handlers.alert_handlers as alert_handlers

    async def noop(*args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr(alert_handlers, "check_alert", noop)

    query = DummyQuery(DummyMessage(), "confirm_entry")
    update_confirm = cast(Update, SimpleNamespace(callback_query=query))
    await router.callback_router(update_confirm, context)

    assert len(DummySession.added_entries) == 1
    saved = DummySession.added_entries[0]
    assert saved.carbs_g == 30.0
    assert saved.sugar_before == 5.5
    assert "pending_entry" not in user_data
    assert query.edited == ["✅ Запись сохранена в дневник!"]
