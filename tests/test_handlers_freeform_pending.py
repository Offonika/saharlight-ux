import datetime
from types import SimpleNamespace, TracebackType
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.dose_handlers as handlers


class DummyMessage:
    def __init__(self, text: str) -> None:
        self.text: str = text
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_freeform_handler_edits_pending_entry_keeps_state() -> None:
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

    await handlers.freeform_handler(update, context)

    assert context.user_data["pending_entry"]["dose"] == 3.5
    assert context.user_data["pending_entry"]["carbs_g"] == 30.0
    assert "pending_entry" in context.user_data
    assert message.replies


@pytest.mark.asyncio
async def test_freeform_handler_adds_sugar_to_photo_entry() -> None:
    entry = {
        "telegram_id": 1,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
        "carbs_g": 20.0,
        "xe": 2.0,
        "dose": 5.0,
        "sugar_before": None,
        "photo_path": "photos/img.jpg",
    }
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

        def get(self, model, user_id):
            return SimpleNamespace(icr=10.0, cf=1.0, target_bg=6.0)

    session_factory = cast(type(handlers.SessionLocal), lambda: DummySession())
    handlers.SessionLocal = session_factory
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

    assert context.user_data["pending_entry"]["sugar_before"] == 5.6
    assert "pending_entry" in context.user_data
    text = message.replies[0]
    assert "5.6 ммоль/л" in text


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

    assert context.user_data["pending_entry"]["sugar_before"] == 4.2
    assert "pending_entry" in context.user_data