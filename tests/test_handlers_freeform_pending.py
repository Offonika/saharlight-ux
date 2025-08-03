import datetime
from types import SimpleNamespace

import pytest
import diabetes.dose_handlers as handlers


class DummyMessage:
    def __init__(self, text):
        self.text = text
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append((text, kwargs))


@pytest.mark.asyncio
async def test_freeform_handler_edits_pending_entry_keeps_state():
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
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data={"pending_entry": entry})

    await handlers.freeform_handler(update, context)

    assert context.user_data["pending_entry"]["dose"] == 3.5
    assert context.user_data["pending_entry"]["carbs_g"] == 30.0
    assert "pending_entry" in context.user_data
    assert message.replies


@pytest.mark.asyncio
async def test_freeform_handler_adds_sugar_to_photo_entry():
    entry = {
        "telegram_id": 1,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
        "carbs_g": 20.0,
        "xe": 2.0,
        "dose": 5.0,
        "sugar_before": None,
        "photo_path": "photos/img.jpg",
    }
    message = DummyMessage("5,6")
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data={"pending_entry": entry})

    await handlers.freeform_handler(update, context)

    assert context.user_data["pending_entry"]["sugar_before"] == 5.6
    assert "pending_entry" in context.user_data
    text, _ = message.replies[0]
    assert "5.6 ммоль/л" in text


@pytest.mark.asyncio
async def test_freeform_handler_sugar_only_flow():
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
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data={"pending_entry": entry})

    await handlers.freeform_handler(update, context)

    assert context.user_data["pending_entry"]["sugar_before"] == 4.2
    assert "pending_entry" in context.user_data
