import datetime
from types import SimpleNamespace, TracebackType
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.gpt_handlers as handlers
from sqlalchemy.orm import Session, sessionmaker
from services.api.app.diabetes.handlers import EntryData


class DummyMessage:
    def __init__(self, text: str) -> None:
        self.text: str = text
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_freeform_handler_edits_pending_entry_keeps_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry = {
        "telegram_id": 1,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
        "carbs_g": 20.0,
        "xe": 2.0,
        "dose": 5.0,
        "sugar_before": 4.5,
        "photo_path": "photos/img.jpg",
    }
    message = DummyMessage("dose=3.5 carbs=30")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"pending_entry": entry}),
    )

    async def fake_check_alert(
        update: Update, context: CallbackContext[Any, Any, Any, Any], sugar: float
    ) -> None:
        pass

    class DummySession:
        def __enter__(self) -> "DummySession":
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None:
            pass

        def add(self, obj: Any) -> None:
            pass

    def session_factory() -> DummySession:
        return DummySession()

    monkeypatch.setattr(handlers, "run_db", None)
    monkeypatch.setattr(handlers, "SessionLocal", session_factory)
    monkeypatch.setattr(handlers, "commit", lambda session: True)
    monkeypatch.setattr(handlers, "check_alert", fake_check_alert)

    await handlers.freeform_handler(update, context)

    user_data = cast(dict[str, Any], context.user_data)
    assert "pending_entry" not in user_data
    assert message.replies and message.replies[0].startswith("✅ Запись сохранена")


@pytest.mark.asyncio
async def test_freeform_handler_adds_sugar_to_photo_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry = {
        "telegram_id": 1,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
        "carbs_g": 20.0,
        "xe": 2.0,
        "dose": 5.0,
        "sugar_before": None,
        "photo_path": "photos/img.jpg",
    }

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
    handlers.SessionLocal = session_factory

    monkeypatch.setattr(handlers, "run_db", None)
    message = DummyMessage("5,6")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"pending_entry": entry}),
    )

    await handlers.freeform_handler(update, context)

    assert context.user_data is not None
    user_data = context.user_data
    pending = user_data.get("pending_entry")
    assert pending is not None
    assert pending["sugar_before"] == 5.6
    assert "pending_entry" in user_data
    assert message.replies
    text = message.replies[0]
    assert "5.6\u202fммоль/л" in text


@pytest.mark.asyncio
async def test_freeform_handler_sugar_only_flow() -> None:
    entry = {
        "telegram_id": 1,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
        "xe": None,
        "carbs_g": None,
        "dose": None,
        "sugar_before": None,
        "photo_path": None,
    }
    message = DummyMessage("4.2")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"pending_entry": entry}),
    )

    await handlers.freeform_handler(update, context)

    assert context.user_data is not None
    user_data = context.user_data
    pending = user_data.get("pending_entry")
    assert pending is not None
    assert pending["sugar_before"] == 4.2
    assert "pending_entry" in user_data


@pytest.mark.asyncio
async def test_freeform_handler_prefilled_entry_cleans_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entry: EntryData = {
        "telegram_id": 1,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
        "carbs_g": 20.0,
        "xe": 2.0,
        "dose": 5.0,
        "sugar_before": 4.5,
        "photo_path": "photos/img.jpg",
    }
    message = DummyMessage("dose=3 carbs=30")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    user_data: dict[str, Any] = {"pending_entry": entry}
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data),
    )

    async def fake_save_entry(
        entry_data: EntryData,
        *,
        SessionLocal: Any,
        commit: Any,
    ) -> bool:
        return True

    async def fake_check_alert(
        update: Update, context: CallbackContext[Any, Any, Any, Any], sugar: float
    ) -> None:
        pass

    monkeypatch.setattr(handlers, "_save_entry", fake_save_entry)

    await handlers.freeform_handler(update, context, check_alert=fake_check_alert)

    assert "pending_entry" not in user_data
    assert "pending_fields" not in user_data
    assert message.replies and message.replies[0].startswith("✅ Запись сохранена")


@pytest.mark.asyncio
async def test_freeform_handler_quick_updates_cleans_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_data: dict[str, Any] = {}
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data),
    )

    calls: list[EntryData] = []

    async def fake_save_entry(
        entry_data: EntryData,
        *,
        SessionLocal: Any,
        commit: Any,
    ) -> bool:
        calls.append(entry_data)
        return True

    async def fake_check_alert(
        update: Update, context: CallbackContext[Any, Any, Any, Any], sugar: float
    ) -> None:
        pass

    monkeypatch.setattr(handlers, "_save_entry", fake_save_entry)

    msg1 = DummyMessage("dose=3 carbs=30")
    update1 = cast(
        Update,
        SimpleNamespace(message=msg1, effective_user=SimpleNamespace(id=1)),
    )
    await handlers.freeform_handler(update1, context, check_alert=fake_check_alert)
    assert user_data.get("pending_fields") == ["sugar", "xe"]

    msg2 = DummyMessage("5")
    update2 = cast(
        Update,
        SimpleNamespace(message=msg2, effective_user=SimpleNamespace(id=1)),
    )
    await handlers.freeform_handler(update2, context, check_alert=fake_check_alert)
    assert user_data.get("pending_fields") == ["xe"]

    msg3 = DummyMessage("2")
    update3 = cast(
        Update,
        SimpleNamespace(message=msg3, effective_user=SimpleNamespace(id=1)),
    )
    await handlers.freeform_handler(update3, context, check_alert=fake_check_alert)

    assert calls
    assert "pending_entry" not in user_data
    assert "pending_fields" not in user_data
    assert msg3.replies and msg3.replies[0].startswith("✅ Запись сохранена")
