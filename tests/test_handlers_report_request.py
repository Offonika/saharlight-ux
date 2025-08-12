import datetime
import os
from types import SimpleNamespace
from typing import Any

import pytest


class DummyMessage:
    def __init__(self, text: str = ""):
        self.text = text
        self.replies: list[tuple[str, dict[str, Any]]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append((text, kwargs))


class DummyQuery:
    def __init__(self, data: str):
        self.data = data
        self.edited: list[str] = []

    async def answer(self) -> None:
        pass

    async def edit_message_text(self, text: str, **kwargs: Any) -> None:
        self.edited.append(text)


@pytest.mark.asyncio
async def test_report_request_and_custom_flow(monkeypatch) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
    import services.api.app.diabetes.handlers.reporting_handlers as reporting_handlers
    import services.api.app.diabetes.handlers.dose_handlers as dose_handlers

    message = DummyMessage()
    update = SimpleNamespace(
        message=message, effective_user=SimpleNamespace(id=1)
    )
    context = SimpleNamespace(user_data={})

    await reporting_handlers.report_request(update, context)
    assert "awaiting_report_date" not in context.user_data
    assert any("Выберите период" in t[0] for t in message.replies)
    assert message.replies[0][1].get("reply_markup") is not None

    query = DummyQuery("report_period:custom")
    update_cb = SimpleNamespace(
        callback_query=query, effective_user=SimpleNamespace(id=1)
    )

    await reporting_handlers.report_period_callback(update_cb, context)

    assert context.user_data.get("awaiting_report_date") is True
    assert any("YYYY-MM-DD" in text for text in query.edited)

    called = {}

    async def dummy_send_report(
        update, context, date_from, period_label, query=None
    ) -> None:
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


@pytest.mark.asyncio
async def test_report_period_callback_week(monkeypatch) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
    import services.api.app.diabetes.handlers.reporting_handlers as reporting_handlers

    called: dict[str, datetime.datetime | str] = {}

    async def dummy_send_report(
        update, context, date_from, period_label, query=None
    ) -> None:
        called["date_from"] = date_from
        called["period_label"] = period_label

    monkeypatch.setattr(reporting_handlers, "send_report", dummy_send_report)

    fixed_now = datetime.datetime(2024, 1, 10, tzinfo=datetime.timezone.utc)

    class DummyDateTime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    monkeypatch.setattr(reporting_handlers.datetime, "datetime", DummyDateTime)

    query = DummyQuery("report_period:week")
    update_cb = SimpleNamespace(
        callback_query=query, effective_user=SimpleNamespace(id=1)
    )
    context = SimpleNamespace(user_data={})

    await reporting_handlers.report_period_callback(update_cb, context)

    expected = (fixed_now - datetime.timedelta(days=7)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    assert called["date_from"] == expected
    assert called["period_label"] == "последнюю неделю"
