import datetime
from types import SimpleNamespace
import os

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
import diabetes.openai_utils as openai_utils  # noqa: F401
import diabetes.dose_handlers as dose_handlers


class DummyMessage:
    def __init__(self, text):
        self.text = text
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


@pytest.mark.asyncio
async def test_entry_without_dose_has_no_unit(monkeypatch):
    pending_entry = {
        "telegram_id": 1,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
        "xe": 2.0,
    }
    context = SimpleNamespace(
        user_data={"pending_entry": pending_entry, "pending_fields": ["sugar"]}
    )
    message = DummyMessage("5.5")
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))

    class DummySession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

        def add(self, entry):
            self.entry = entry

    async def noop(*args, **kwargs):
        pass

    monkeypatch.setattr(dose_handlers, "SessionLocal", lambda: DummySession())
    monkeypatch.setattr(dose_handlers, "commit_session", lambda session: True)
    monkeypatch.setattr(dose_handlers, "check_alert", noop)
    monkeypatch.setattr(dose_handlers, "menu_keyboard", None)

    await dose_handlers.freeform_handler(update, context)

    assert not context.user_data
    assert message.replies
    text = message.replies[0]
    assert "доза —" in text
    assert "Ед" not in text

