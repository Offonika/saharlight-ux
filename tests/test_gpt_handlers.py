from types import SimpleNamespace
from typing import Any, cast

import datetime
import pytest
from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.gpt_handlers as gpt_handlers


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.texts: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_chat_with_gpt_replies() -> None:
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    await gpt_handlers.chat_with_gpt(update, context)
    assert message.texts == ["🗨️ Чат с GPT временно недоступен."]


@pytest.mark.asyncio
async def test_freeform_handler_awaiting_report_cancel() -> None:
    message = DummyMessage("назад")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"awaiting_report_date": True}),
    )
    await gpt_handlers.freeform_handler(update, context)
    assert message.texts == ["📋 Выберите действие:"]
    assert "awaiting_report_date" not in cast(dict[str, Any], context.user_data)


@pytest.mark.asyncio
async def test_freeform_handler_awaiting_report_invalid_date() -> None:
    message = DummyMessage("not-a-date")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"awaiting_report_date": True}),
    )
    await gpt_handlers.freeform_handler(update, context)
    assert message.texts == ["❗ Некорректная дата. Используйте формат YYYY-MM-DD."]


@pytest.mark.asyncio
async def test_freeform_handler_awaiting_report_valid_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[datetime.datetime] = []

    async def fake_send_report(
        update: Update,
        context: CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        date_from: datetime.datetime,
        label: str,
    ) -> None:
        called.append(date_from)

    monkeypatch.setattr(gpt_handlers, "send_report", fake_send_report)
    message = DummyMessage("2024-01-02")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"awaiting_report_date": True}),
    )
    await gpt_handlers.freeform_handler(update, context)
    assert called and called[0].date() == datetime.date(2024, 1, 2)


@pytest.mark.asyncio
async def test_freeform_handler_pending_entry_value_error() -> None:
    message = DummyMessage("abc")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"pending_entry": {}, "pending_fields": ["xe"]}),
    )
    await gpt_handlers.freeform_handler(update, context)
    assert message.texts == ["Введите число ХЕ."]


@pytest.mark.asyncio
async def test_freeform_handler_pending_entry_negative() -> None:
    message = DummyMessage("-1")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"pending_entry": {}, "pending_fields": ["dose"]}),
    )
    await gpt_handlers.freeform_handler(update, context)
    assert message.texts == ["Доза инсулина не может быть отрицательной."]


@pytest.mark.asyncio
async def test_freeform_handler_pending_entry_next_field() -> None:
    message = DummyMessage("5")
    user_data: dict[str, Any] = {
        "pending_entry": {},
        "pending_fields": ["sugar", "xe"],
    }
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data),
    )
    await gpt_handlers.freeform_handler(update, context)
    assert user_data["pending_entry"]["sugar_before"] == 5
    assert user_data["pending_fields"] == ["xe"]
    assert message.texts == ["Введите количество ХЕ."]


@pytest.mark.asyncio
async def test_freeform_handler_smart_input_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage("bad")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )

    def fake_smart_input(text: str) -> dict[str, float | None]:
        raise ValueError("mismatched unit for xe")

    monkeypatch.setattr(gpt_handlers, "smart_input", fake_smart_input)
    await gpt_handlers.freeform_handler(update, context)
    assert message.texts == ["❗ ХЕ указываются числом, без ммоль/л и ед."]


@pytest.mark.asyncio
async def test_freeform_handler_quick_update_pending_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage("sugar=5")
    user_data: dict[str, Any] = {"pending_entry": {}, "edit_id": None}
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data),
    )

    def fake_smart_input(text: str) -> dict[str, float | None]:
        return {"sugar": 5.0, "xe": None, "dose": None}

    monkeypatch.setattr(gpt_handlers, "smart_input", fake_smart_input)
    await gpt_handlers.freeform_handler(update, context)
    assert user_data["pending_entry"]["sugar_before"] == 5.0
    assert message.texts == ["Данные обновлены."]


@pytest.mark.asyncio
async def test_freeform_handler_quick_entry_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage("sugar=5 xe=1 dose=2")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )

    def fake_smart_input(text: str) -> dict[str, float | None]:
        return {"sugar": 5.0, "xe": 1.0, "dose": 2.0}

    async def fake_run_db(func: Any, sessionmaker: Any) -> bool:
        return True

    async def fake_check_alert(
        update: Update, context: CallbackContext[Any, Any, Any, Any], sugar: float
    ) -> None:
        return None

    monkeypatch.setattr(gpt_handlers, "smart_input", fake_smart_input)
    monkeypatch.setattr(gpt_handlers, "run_db", fake_run_db)
    monkeypatch.setattr(gpt_handlers, "check_alert", fake_check_alert)

    await gpt_handlers.freeform_handler(update, context)
    assert message.texts[0].startswith("✅ Запись сохранена")


@pytest.mark.asyncio
async def test_freeform_handler_run_db_runtime_error_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage("sugar=5 xe=1 dose=2")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )

    def fake_smart_input(text: str) -> dict[str, float | None]:
        return {"sugar": 5.0, "xe": 1.0, "dose": 2.0}

    class DummySession:
        added: list[Any] = []

        def __enter__(self) -> "DummySession":
            return self

        def __exit__(self, *args: Any) -> None:  # pragma: no cover - simple helper
            pass

        def add(self, entry: Any) -> None:
            self.added.append(entry)

    session_factory = cast(Any, lambda: DummySession())
    monkeypatch.setattr(gpt_handlers, "SessionLocal", session_factory)

    async def boom(*args: Any, **kwargs: Any) -> bool:
        raise RuntimeError("fail")

    async def fake_check_alert(*args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr(gpt_handlers, "smart_input", fake_smart_input)
    monkeypatch.setattr(gpt_handlers, "run_db", boom)
    monkeypatch.setattr(gpt_handlers, "commit", lambda session: True)
    monkeypatch.setattr(gpt_handlers, "check_alert", fake_check_alert)

    await gpt_handlers.freeform_handler(update, context)

    assert DummySession.added
    assert message.texts[0].startswith("✅ Запись сохранена")


@pytest.mark.asyncio
async def test_freeform_handler_parse_command_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage("text")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )

    def fake_smart_input(text: str) -> dict[str, float | None]:
        return {"sugar": None, "xe": None, "dose": None}

    async def fake_parse_command(text: str) -> dict[str, Any] | None:
        return None

    monkeypatch.setattr(gpt_handlers, "smart_input", fake_smart_input)
    monkeypatch.setattr(gpt_handlers, "parse_command", fake_parse_command)

    await gpt_handlers.freeform_handler(update, context)
    assert message.texts == ["Не понял, воспользуйтесь /help или кнопками меню"]
