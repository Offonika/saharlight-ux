import datetime as dt
import os
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext
from tests.helpers import make_update


class DummyMessage:
    def __init__(self, text: str = "") -> None:
        self.text = text
        self.replies: list[tuple[str, dict[str, Any]]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append((text, kwargs))


class DummyQuery:
    def __init__(self, data: str) -> None:
        self.data = data
        self.edited: list[str] = []

    async def answer(self) -> None:
        pass

    async def edit_message_text(self, text: str, **kwargs: Any) -> None:
        self.edited.append(text)


@pytest.mark.asyncio
async def test_report_request_and_custom_flow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
    import services.api.app.diabetes.handlers.reporting_handlers as reporting_handlers
    import services.api.app.diabetes.handlers.dose_handlers as dose_handlers

    message = DummyMessage()
    update = make_update(
        message=message, effective_user=SimpleNamespace(id=1)
    )
    context = cast(
        CallbackContext[Any, Any, Any, Any], SimpleNamespace(user_data={})
    )

    await reporting_handlers.report_request(update, context)
    assert "awaiting_report_date" not in context.user_data
    assert any("Выберите период" in t[0] for t in message.replies)
    assert message.replies[0][1].get("reply_markup") is not None

    query = DummyQuery("report_period:custom")
    update_cb = make_update(
        callback_query=query, effective_user=SimpleNamespace(id=1)
    )

    await reporting_handlers.report_period_callback(update_cb, context)

    assert context.user_data.get("awaiting_report_date") is True
    assert any("YYYY-MM-DD" in text for text in query.edited)

    called = {}

    async def dummy_send_report(
        update: Any, context: Any, date_from: Any, period_label: Any, query: Any=None
    ) -> None:
        called["called"] = True
        expected = dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)
        assert date_from == expected

    monkeypatch.setattr(dose_handlers, "send_report", dummy_send_report)

    update2 = cast(
        Update,
        SimpleNamespace(
            message=DummyMessage(text="2024-01-01"),
            effective_user=SimpleNamespace(id=1),
        ),
    )
    await dose_handlers.freeform_handler(update2, context)

    assert called.get("called")
    assert "awaiting_report_date" not in context.user_data


@pytest.mark.asyncio
async def test_report_period_callback_week(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
    import services.api.app.diabetes.handlers.reporting_handlers as reporting_handlers

    called: dict[str, dt.datetime | str] = {}

    async def dummy_send_report(
        update: Any, context: Any, date_from: Any, period_label: Any, query: Any=None
    ) -> None:
        called["date_from"] = date_from
        called["period_label"] = period_label

    monkeypatch.setattr(reporting_handlers, "send_report", dummy_send_report)

    class DummyDateTime(dt.datetime):
        @classmethod
        def now(cls, tz: dt.tzinfo | None = None) -> dt.datetime:
            return fixed_now

    fixed_now = DummyDateTime(2024, 1, 10, tzinfo=dt.timezone.utc)

    monkeypatch.setattr(reporting_handlers.datetime, "datetime", DummyDateTime)

    query = DummyQuery("report_period:week")
    update_cb = make_update(
        callback_query=query, effective_user=SimpleNamespace(id=1)
    )
    context = cast(
        CallbackContext[Any, Any, Any, Any], SimpleNamespace(user_data={})
    )

    await reporting_handlers.report_period_callback(update_cb, context)

    expected = (fixed_now - dt.timedelta(days=7)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    assert called["date_from"] == expected
    assert called["period_label"] == "последнюю неделю"
