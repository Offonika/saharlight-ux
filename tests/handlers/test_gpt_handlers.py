"""Tests for :mod:`gpt_handlers` freeform logic."""

from __future__ import annotations

import datetime as dt
from types import SimpleNamespace
from typing import Any, cast

from telegram import Update
from telegram.ext import CallbackContext

import pytest

import services.api.app.diabetes.handlers.gpt_handlers as gpt_handlers


class DummyMessage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.replies: list[tuple[str, dict[str, Any]]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append((text, kwargs))


def make_update(message: DummyMessage) -> Update:
    return cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )


def make_context(
    user_data: dict[str, Any] | None = None,
) -> CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]]:
    return cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data or {}),
    )


@pytest.mark.asyncio
async def test_report_date_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    message = DummyMessage("/cancel")
    update = make_update(message)
    user_data: dict[str, Any] = {"awaiting_report_date": True}
    context = make_context(user_data)
    await gpt_handlers.freeform_handler(update, context)
    assert "awaiting_report_date" not in user_data
    assert message.replies[0][0].startswith("📋 Выберите действие")


@pytest.mark.asyncio
async def test_report_date_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    message = DummyMessage("not a date")
    update = make_update(message)
    user_data: dict[str, Any] = {"awaiting_report_date": True}
    context = make_context(user_data)
    await gpt_handlers.freeform_handler(update, context)
    assert user_data.get("awaiting_report_date") is True
    assert "Некорректная дата" in message.replies[0][0]


@pytest.mark.asyncio
async def test_report_date_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, Any] = {}

    async def fake_send_report(
        update: Any, context: Any, date_from: dt.datetime, period: str
    ) -> None:
        called["date_from"] = date_from
        called["period"] = period

    monkeypatch.setattr(gpt_handlers, "send_report", fake_send_report)
    message = DummyMessage("2024-02-01")
    update = make_update(message)
    user_data: dict[str, Any] = {"awaiting_report_date": True}
    context = make_context(user_data)
    await gpt_handlers.freeform_handler(update, context)
    assert "awaiting_report_date" not in user_data
    assert called["date_from"].date() == dt.date(2024, 2, 1)
    assert called["period"] == "указанный период"


@pytest.mark.asyncio
async def test_pending_entry_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    message = DummyMessage("abc")
    update = make_update(message)
    user_data = {"pending_entry": {}, "pending_fields": ["sugar"]}
    context = make_context(user_data)
    await gpt_handlers.freeform_handler(update, context)
    assert "сахар числом" in message.replies[0][0]


@pytest.mark.asyncio
async def test_pending_entry_negative(monkeypatch: pytest.MonkeyPatch) -> None:
    message = DummyMessage("-1")
    update = make_update(message)
    user_data = {"pending_entry": {}, "pending_fields": ["xe"]}
    context = make_context(user_data)
    await gpt_handlers.freeform_handler(update, context)
    assert "не может быть отрицательным" in message.replies[0][0]


@pytest.mark.asyncio
async def test_pending_entry_next_field(monkeypatch: pytest.MonkeyPatch) -> None:
    message = DummyMessage("1")
    update = make_update(message)
    entry: dict[str, Any] = {}
    user_data = {"pending_entry": entry, "pending_fields": ["xe", "dose"]}
    context = make_context(user_data)
    await gpt_handlers.freeform_handler(update, context)
    assert entry["xe"] == 1
    assert user_data["pending_fields"] == ["dose"]
    assert "дозу инсулина" in message.replies[0][0]


@pytest.mark.asyncio
async def test_pending_entry_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    message = DummyMessage("5")
    update = make_update(message)
    entry = {"telegram_id": 1, "event_time": dt.datetime.now(dt.timezone.utc)}
    user_data = {"pending_entry": entry, "pending_fields": ["sugar"]}

    async def fake_run_db(func: Any, sessionmaker: Any = None) -> bool:
        class DummySession:
            def add(self, obj: Any) -> None:  # noqa: D401 - no action
                pass

        result = func(DummySession())
        return bool(result)

    async def fake_check_alert(update: Any, context: Any, sugar: float) -> None:
        pass

    monkeypatch.setattr(gpt_handlers, "run_db", fake_run_db)
    monkeypatch.setattr(gpt_handlers, "commit", lambda session: True)
    monkeypatch.setattr(gpt_handlers, "check_alert", fake_check_alert)
    context = make_context(user_data)
    await gpt_handlers.freeform_handler(update, context)
    assert "pending_entry" not in user_data
    assert message.replies[0][0].startswith("✅ Запись сохранена")


@pytest.mark.asyncio
async def test_smart_input_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_smart_input(text: str) -> Any:
        raise ValueError("mismatched unit for sugar")

    monkeypatch.setattr(gpt_handlers, "smart_input", fake_smart_input)
    message = DummyMessage("bogus")
    update = make_update(message)
    context = make_context({})
    await gpt_handlers.freeform_handler(update, context)
    assert "Сахар указывается" in message.replies[0][0]


@pytest.mark.asyncio
async def test_smart_input_negative(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_smart_input(text: str) -> dict[str, float | None]:
        return {"sugar": -1.0, "xe": None, "dose": None}

    monkeypatch.setattr(gpt_handlers, "smart_input", fake_smart_input)
    message = DummyMessage("sugar=-1")
    update = make_update(message)
    context = make_context({})
    await gpt_handlers.freeform_handler(update, context)
    assert "не могут быть отрицательными" in message.replies[0][0]


@pytest.mark.asyncio
async def test_smart_input_missing_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_smart_input(text: str) -> dict[str, float | None]:
        return {"sugar": 5.0, "xe": None, "dose": None}

    monkeypatch.setattr(gpt_handlers, "smart_input", fake_smart_input)
    message = DummyMessage("sugar=5")
    update = make_update(message)
    user_data: dict[str, Any] = {}
    context = make_context(user_data)
    await gpt_handlers.freeform_handler(update, context)
    assert user_data["pending_fields"] == ["xe", "dose"]
    assert "количество ХЕ" in message.replies[0][0]


@pytest.mark.asyncio
async def test_smart_input_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_smart_input(text: str) -> dict[str, float | None]:
        return {"sugar": 5.0, "xe": 1.0, "dose": 2.0}

    async def fake_run_db(func: Any, sessionmaker: Any = None) -> bool:
        class DummySession:
            def add(self, obj: Any) -> None:
                pass

        result = func(DummySession())
        return bool(result)

    async def fake_check_alert(update: Any, context: Any, sugar: float) -> None:
        pass

    monkeypatch.setattr(gpt_handlers, "smart_input", fake_smart_input)
    monkeypatch.setattr(gpt_handlers, "run_db", fake_run_db)
    monkeypatch.setattr(gpt_handlers, "commit", lambda session: True)
    monkeypatch.setattr(gpt_handlers, "check_alert", fake_check_alert)
    message = DummyMessage("all")
    update = make_update(message)
    context = make_context({})
    await gpt_handlers.freeform_handler(update, context)
    assert message.replies[0][0].startswith("✅ Запись сохранена")


@pytest.mark.asyncio
async def test_parse_command_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_smart_input(text: str) -> dict[str, float | None]:
        return {"sugar": None, "xe": None, "dose": None}

    async def fake_parse(text: str) -> dict[str, Any] | None:
        return None

    monkeypatch.setattr(gpt_handlers, "smart_input", fake_smart_input)
    monkeypatch.setattr(gpt_handlers, "parse_command", fake_parse)
    message = DummyMessage("unknown")
    update = make_update(message)
    context = make_context({})
    await gpt_handlers.freeform_handler(update, context)
    assert message.replies[0][0].startswith("Не понял")


@pytest.mark.asyncio
async def test_parse_command_negative(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_smart_input(text: str) -> dict[str, float | None]:
        return {"sugar": None, "xe": None, "dose": None}

    async def fake_parse(text: str) -> dict[str, Any]:
        return {"action": "add_entry", "fields": {"sugar_before": -1}}

    monkeypatch.setattr(gpt_handlers, "smart_input", fake_smart_input)
    monkeypatch.setattr(gpt_handlers, "parse_command", fake_parse)
    message = DummyMessage("bad")
    update = make_update(message)
    context = make_context({})
    await gpt_handlers.freeform_handler(update, context)
    assert "не могут быть отрицательными" in message.replies[0][0]


@pytest.mark.asyncio
async def test_parse_command_valid_time(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_smart_input(text: str) -> dict[str, float | None]:
        return {"sugar": None, "xe": None, "dose": None}

    async def fake_parse(text: str) -> dict[str, Any]:
        return {
            "action": "add_entry",
            "fields": {"sugar_before": 5, "xe": 1, "dose": 2},
            "time": "12:34",
        }

    monkeypatch.setattr(gpt_handlers, "smart_input", fake_smart_input)
    monkeypatch.setattr(gpt_handlers, "parse_command", fake_parse)
    message = DummyMessage("entry")
    update = make_update(message)
    user_data: dict[str, Any] = {}
    context = make_context(user_data)
    await gpt_handlers.freeform_handler(update, context)
    assert user_data["pending_entry"]["xe"] == 1
    assert "Расчёт завершён" in message.replies[0][0]

