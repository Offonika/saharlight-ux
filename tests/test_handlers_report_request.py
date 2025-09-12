from __future__ import annotations

import datetime as dt
import os
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext


class DummyMessage:
    def __init__(self, text: str = "") -> None:
        self.text: str = text
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
        self.answers: list[tuple[str | None, bool]] = []

    async def answer(
        self, text: str | None = None, show_alert: bool = False
    ) -> None:
        self.answers.append((text, show_alert))

    async def edit_message_text(self, text: str, **kwargs: Any) -> None:
        self.edited.append(text)


@pytest.mark.asyncio
async def test_report_request_and_custom_flow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.handlers.reporting_handlers as reporting_handlers
    import services.api.app.diabetes.handlers.dose_calc as dose_calc

    message = DummyMessage()
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )

    await reporting_handlers.report_request(update, context)
    assert context.user_data is not None
    user_data = context.user_data
    assert "awaiting_report_date" not in user_data
    assert any("Выберите период" in t for t in message.replies)
    assert message.kwargs
    first_kwargs = message.kwargs[0]
    assert first_kwargs is not None
    assert first_kwargs.get("reply_markup") is not None

    query = DummyQuery(DummyMessage(), "report_period:custom")
    update_cb = cast(
        Update,
        SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1)),
    )

    await reporting_handlers.report_period_callback(update_cb, context)

    assert context.user_data is not None
    user_data = context.user_data
    assert user_data.get("awaiting_report_date") is True
    assert query.edited
    assert any("YYYY-MM-DD" in text for text in query.edited)

    called: dict[str, bool] = {}

    async def dummy_send_report(
        update: Update,
        context: CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        date_from: dt.datetime,
        period_label: str,
        query: DummyQuery | None = None,
    ) -> None:
        called["called"] = True
        expected = dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc)
        assert date_from == expected

    monkeypatch.setattr(dose_calc, "send_report", dummy_send_report)

    update2 = cast(
        Update,
        SimpleNamespace(
            message=DummyMessage(text="2024-01-01"),
            effective_user=SimpleNamespace(id=1),
        ),
    )
    await dose_calc.freeform_handler(update2, context)

    called_flag = called.get("called")
    assert called_flag is not None
    assert context.user_data is not None
    user_data = context.user_data
    assert "awaiting_report_date" not in user_data


@pytest.mark.asyncio
async def test_report_period_callback_week(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
    import services.api.app.diabetes.handlers.reporting_handlers as reporting_handlers

    called: dict[str, dt.datetime | str] = {}

    async def dummy_send_report(
        update: Update,
        context: CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        date_from: dt.datetime,
        period_label: str,
        query: DummyQuery | None = None,
    ) -> None:
        called["date_from"] = date_from
        called["period_label"] = period_label

    monkeypatch.setattr(reporting_handlers, "send_report", dummy_send_report)

    class DummyDateTime(dt.datetime):
        @classmethod
        def now(cls, tz: dt.tzinfo | None = None) -> "DummyDateTime":
            return fixed_now

    fixed_now = DummyDateTime(2024, 1, 10, tzinfo=dt.timezone.utc)

    monkeypatch.setattr(reporting_handlers.datetime, "datetime", DummyDateTime)

    query = DummyQuery(DummyMessage(), "report_period:week")
    update_cb = cast(
        Update,
        SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={})
    )

    await reporting_handlers.report_period_callback(update_cb, context)

    expected = (fixed_now - dt.timedelta(days=7)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    date_from = called.get("date_from")
    assert date_from is not None
    assert date_from == expected
    period_label = called.get("period_label")
    assert period_label is not None
    assert period_label == "последнюю неделю"


@pytest.mark.asyncio
async def test_report_period_callback_invalid_data() -> None:
    import services.api.app.diabetes.handlers.reporting_handlers as reporting_handlers

    query = DummyQuery(DummyMessage(), "report_period")
    update_cb = cast(
        Update,
        SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )

    await reporting_handlers.report_period_callback(update_cb, context)

    assert query.answers
    text, alert = query.answers[0]
    assert text is not None
    assert "некоррект" in text.lower()
    assert alert is True
    assert not query.edited
