import datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Message, Update
from telegram.ext import CallbackContext

from services.api.app.diabetes.handlers import UserData, gpt_handlers


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.texts: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_handle_report_request_cancel() -> None:
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=cast(Message, message)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    user_data: dict[str, Any] = {"awaiting_report_date": True}
    deps = gpt_handlers.default_deps()
    handled = await gpt_handlers._handle_report_request(
        "назад",
        cast(UserData, user_data),
        cast(Message, message),
        update,
        context,
        deps,
    )
    assert handled is True
    assert "awaiting_report_date" not in user_data
    assert message.texts == ["📋 Выберите действие:"]


@pytest.mark.asyncio
async def test_handle_report_request_invalid_date() -> None:
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=cast(Message, message)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    user_data: dict[str, Any] = {"awaiting_report_date": True}
    deps = gpt_handlers.default_deps()
    handled = await gpt_handlers._handle_report_request(
        "bad-date",
        cast(UserData, user_data),
        cast(Message, message),
        update,
        context,
        deps,
    )
    assert handled is True
    assert message.texts == ["❗ Некорректная дата. Используйте формат YYYY-MM-DD."]


@pytest.mark.asyncio
async def test_handle_report_request_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[datetime.datetime] = []

    async def fake_send_report(
        update: Update,
        context: CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        date_from: datetime.datetime,
        label: str,
    ) -> None:
        called.append(date_from)

    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=cast(Message, message)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    user_data: dict[str, Any] = {"awaiting_report_date": True}
    deps = gpt_handlers.default_deps()
    deps.send_report = fake_send_report
    handled = await gpt_handlers._handle_report_request(
        "2024-01-02",
        cast(UserData, user_data),
        cast(Message, message),
        update,
        context,
        deps,
    )
    assert handled is True
    assert called and called[0].date() == datetime.date(2024, 1, 2)


@pytest.mark.asyncio
async def test_handle_pending_entry_value_error() -> None:
    message = DummyMessage("abc")
    update = cast(Update, SimpleNamespace(message=cast(Message, message)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    user_data: dict[str, Any] = {"pending_entry": {}, "pending_fields": ["xe"]}
    deps = gpt_handlers.default_deps()
    handled = await gpt_handlers._handle_pending_entry(
        "abc",
        cast(UserData, user_data),
        cast(Message, message),
        update,
        context,
        1,
        deps,
    )
    assert handled is True
    assert message.texts == ["Введите число ХЕ."]


@pytest.mark.asyncio
async def test_handle_pending_entry_negative() -> None:
    message = DummyMessage("-1")
    update = cast(Update, SimpleNamespace(message=cast(Message, message)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    user_data: dict[str, Any] = {"pending_entry": {}, "pending_fields": ["dose"]}
    deps = gpt_handlers.default_deps()
    handled = await gpt_handlers._handle_pending_entry(
        "-1",
        cast(UserData, user_data),
        cast(Message, message),
        update,
        context,
        1,
        deps,
    )
    assert handled is True
    assert message.texts == ["Доза инсулина не может быть отрицательной."]


@pytest.mark.asyncio
async def test_handle_pending_entry_next_field() -> None:
    message = DummyMessage("5")
    user_data: dict[str, Any] = {"pending_entry": {}, "pending_fields": ["sugar", "xe"]}
    update = cast(Update, SimpleNamespace(message=cast(Message, message)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    deps = gpt_handlers.default_deps()
    handled = await gpt_handlers._handle_pending_entry(
        "5",
        cast(UserData, user_data),
        cast(Message, message),
        update,
        context,
        1,
        deps,
    )
    assert handled is True
    assert user_data["pending_entry"]["sugar_before"] == 5
    assert user_data["pending_fields"] == ["xe"]
    assert message.texts == ["Введите количество ХЕ."]


@pytest.mark.asyncio
async def test_handle_pending_entry_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    message = DummyMessage("5")
    entry: dict[str, Any] = {
        "telegram_id": 1,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
    }
    user_data: dict[str, Any] = {"pending_entry": entry, "pending_fields": ["sugar"]}
    update = cast(Update, SimpleNamespace(message=cast(Message, message)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    async def fake_run_db(func: Any, sessionmaker: Any) -> bool:
        class DummySession:
            def add(self, obj: Any) -> None:
                pass

        return bool(func(DummySession()))

    async def fake_check_alert(
        update: Update, context: CallbackContext[Any, Any, Any, Any], sugar: float
    ) -> None:
        return None

    monkeypatch.setattr(gpt_handlers, "run_db", fake_run_db)
    deps = gpt_handlers.default_deps()
    deps.commit = lambda session: True
    deps.check_alert = fake_check_alert

    handled = await gpt_handlers._handle_pending_entry(
        "5",
        cast(UserData, user_data),
        cast(Message, message),
        update,
        context,
        1,
        deps,
    )
    assert handled is True
    assert message.texts and message.texts[0].startswith("✅ Запись сохранена")
    assert "pending_entry" not in user_data
    assert "pending_fields" not in user_data
