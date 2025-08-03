import os
import datetime
from types import SimpleNamespace

import pytest


class DummyMessage:
    def __init__(self, text: str = ""):
        self.text = text
        self.texts: list[str] = []

    async def reply_text(self, text, **kwargs):
        self.texts.append(text)


@pytest.mark.asyncio
async def test_report_request_flag_set_and_cleared(monkeypatch):
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import diabetes.openai_utils as openai_utils  # noqa: F401
    import diabetes.reporting_handlers as reporting_handlers
    import diabetes.dose_handlers as dose_handlers

    message = DummyMessage()
    update = SimpleNamespace(
        message=message, effective_user=SimpleNamespace(id=1)
    )
    context = SimpleNamespace(user_data={})

    await reporting_handlers.report_request(update, context)
    assert context.user_data.get("awaiting_report_date") is True
    assert any("YYYY-MM-DD" in t for t in message.texts)

    called = {}

    async def dummy_send_report(update, context, date_from, period_label, query=None):
        called["called"] = True
        expected = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
        assert date_from == expected

    monkeypatch.setattr(dose_handlers, "send_report", dummy_send_report)

    update2 = SimpleNamespace(
        message=DummyMessage(text="2024-01-01"),
        effective_user=SimpleNamespace(id=1),
    )
    await dose_handlers.freeform_handler(update2, context)

    assert called.get("called")
    assert "awaiting_report_date" not in context.user_data
