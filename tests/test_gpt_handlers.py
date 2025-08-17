from types import SimpleNamespace
from typing import Any, cast

import datetime
import pytest
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.diabetes.handlers import gpt_handlers


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
async def test_chat_with_gpt_no_message() -> None:
    update = cast(Update, SimpleNamespace(message=None))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    await gpt_handlers.chat_with_gpt(update, context)


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
    assert message.texts == [
        "❗ Некорректная дата. Используйте формат YYYY-MM-DD."
    ]


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
async def test_freeform_handler_pending_entry_value_error_sugar() -> None:
    message = DummyMessage("abc")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"pending_entry": {}, "pending_fields": ["sugar"]}),
    )
    await gpt_handlers.freeform_handler(update, context)
    assert message.texts == ["Введите сахар числом в ммоль/л."]


@pytest.mark.asyncio
async def test_freeform_handler_pending_entry_value_error_dose() -> None:
    message = DummyMessage("abc")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"pending_entry": {}, "pending_fields": ["dose"]}),
    )
    await gpt_handlers.freeform_handler(update, context)
    assert message.texts == ["Введите дозу инсулина числом."]


@pytest.mark.asyncio
async def test_freeform_handler_pending_entry_negative_sugar() -> None:
    message = DummyMessage("-1")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"pending_entry": {}, "pending_fields": ["sugar"]}),
    )
    await gpt_handlers.freeform_handler(update, context)
    assert message.texts == ["Сахар не может быть отрицательным."]


@pytest.mark.asyncio
async def test_freeform_handler_pending_entry_negative_xe() -> None:
    message = DummyMessage("-1")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"pending_entry": {}, "pending_fields": ["xe"]}),
    )
    await gpt_handlers.freeform_handler(update, context)
    assert message.texts == ["Количество ХЕ не может быть отрицательным."]


@pytest.mark.asyncio
async def test_freeform_handler_pending_entry_set_xe() -> None:
    message = DummyMessage("1")
    entry: dict[str, Any] = {}
    user_data = {"pending_entry": entry, "pending_fields": ["xe", "dose"]}
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data),
    )
    await gpt_handlers.freeform_handler(update, context)
    assert entry["xe"] == 1
    assert entry["carbs_g"] == 12
    assert user_data["pending_fields"] == ["dose"]
    assert message.texts == ["Введите дозу инсулина (ед.)."]


@pytest.mark.asyncio
async def test_freeform_handler_pending_entry_prompt_sugar() -> None:
    message = DummyMessage("1")
    user_data = {"pending_entry": {}, "pending_fields": ["xe", "sugar"]}
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data),
    )
    await gpt_handlers.freeform_handler(update, context)
    assert user_data["pending_fields"] == ["sugar"]
    assert message.texts == ["Введите уровень сахара (ммоль/л)."]


@pytest.mark.asyncio
async def test_freeform_handler_smart_input_error(monkeypatch: pytest.MonkeyPatch) -> None:
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
    assert message.texts == [
        "❗ ХЕ указываются числом, без ммоль/л и ед."
    ]


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
async def test_freeform_handler_quick_update_pending_entry_xe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage("xe=2")
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
        return {"sugar": None, "xe": 2.0, "dose": None}

    monkeypatch.setattr(gpt_handlers, "smart_input", fake_smart_input)
    await gpt_handlers.freeform_handler(update, context)
    assert user_data["pending_entry"]["xe"] == 2.0
    assert user_data["pending_entry"]["carbs_g"] == 24.0
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
        class DummySession:
            def add(self, obj: Any) -> None:  # noqa: D401 - no action
                pass

        return bool(func(DummySession()))

    async def fake_check_alert(
        update: Update, context: CallbackContext[Any, Any, Any, Any], sugar: float
    ) -> None:
        return None

    monkeypatch.setattr(gpt_handlers, "smart_input", fake_smart_input)
    monkeypatch.setattr(gpt_handlers, "run_db", fake_run_db)
    monkeypatch.setattr(gpt_handlers, "commit", lambda session: True)
    monkeypatch.setattr(gpt_handlers, "check_alert", fake_check_alert)

    await gpt_handlers.freeform_handler(update, context)
    assert message.texts[0].startswith("✅ Запись сохранена")


@pytest.mark.asyncio
async def test_freeform_handler_quick_missing_sugar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage("xe=1 dose=2")
    user_data: dict[str, Any] = {}
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data),
    )

    def fake_smart_input(text: str) -> dict[str, float | None]:
        return {"sugar": None, "xe": 1.0, "dose": 2.0}

    monkeypatch.setattr(gpt_handlers, "smart_input", fake_smart_input)
    await gpt_handlers.freeform_handler(update, context)
    assert user_data["pending_fields"] == ["sugar"]
    assert message.texts == ["Введите уровень сахара (ммоль/л)."]


@pytest.mark.asyncio
async def test_freeform_handler_quick_missing_dose(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage("sugar=5 xe=1")
    user_data: dict[str, Any] = {}
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data),
    )

    def fake_smart_input(text: str) -> dict[str, float | None]:
        return {"sugar": 5.0, "xe": 1.0, "dose": None}

    monkeypatch.setattr(gpt_handlers, "smart_input", fake_smart_input)
    await gpt_handlers.freeform_handler(update, context)
    assert user_data["pending_fields"] == ["dose"]
    assert message.texts == ["Введите дозу инсулина (ед.)."]


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


@pytest.mark.asyncio
async def test_freeform_handler_smart_input_negative(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage("sugar=-1")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )

    def fake_smart_input(text: str) -> dict[str, float | None]:
        return {"sugar": -1.0, "xe": None, "dose": None}

    monkeypatch.setattr(gpt_handlers, "smart_input", fake_smart_input)
    await gpt_handlers.freeform_handler(update, context)
    assert "не могут быть отрицательными" in message.texts[0]


@pytest.mark.asyncio
async def test_freeform_handler_smart_input_missing_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage("sugar=5")
    user_data: dict[str, Any] = {}
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
    assert user_data["pending_fields"] == ["xe", "dose"]
    assert "количество ХЕ" in message.texts[0]


@pytest.mark.asyncio
async def test_freeform_handler_pending_entry_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage("5")
    entry = {
        "telegram_id": 1,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
    }
    user_data = {"pending_entry": entry, "pending_fields": ["sugar"]}
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data),
    )

    async def fake_run_db(func: Any, sessionmaker: Any) -> bool:
        class DummySession:
            def add(self, obj: Any) -> None:  # noqa: D401 - no action
                pass

        return bool(func(DummySession()))

    async def fake_check_alert(
        update: Update, context: CallbackContext[Any, Any, Any, Any], sugar: float
    ) -> None:
        return None

    monkeypatch.setattr(gpt_handlers, "run_db", fake_run_db)
    monkeypatch.setattr(gpt_handlers, "commit", lambda session: True)
    monkeypatch.setattr(gpt_handlers, "check_alert", fake_check_alert)
    await gpt_handlers.freeform_handler(update, context)
    assert "pending_entry" not in user_data
    assert message.texts[0].startswith("✅ Запись сохранена")


@pytest.mark.asyncio
async def test_freeform_handler_pending_entry_commit_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage("5")
    user_data = {"pending_entry": {}, "pending_fields": ["sugar"]}
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data),
    )

    async def fake_run_db(func: Any, sessionmaker: Any) -> bool:
        return False

    monkeypatch.setattr(gpt_handlers, "run_db", fake_run_db)
    await gpt_handlers.freeform_handler(update, context)
    assert message.texts == ["⚠️ Не удалось сохранить запись."]


@pytest.mark.asyncio
async def test_freeform_handler_pending_entry_numeric_negative() -> None:
    message = DummyMessage("-1")
    user_data = {"pending_entry": {"xe": 1.0}, "pending_fields": []}
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data),
    )
    await gpt_handlers.freeform_handler(update, context)
    assert message.texts == ["Сахар не может быть отрицательным."]


@pytest.mark.asyncio
async def test_freeform_handler_pending_entry_numeric_add_carbs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage("5")
    entry = {"xe": 1.0}
    user_data = {"pending_entry": entry, "pending_fields": []}
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data),
    )
    async def fake_run_db(func: Any, sessionmaker: Any = None) -> Any:
        return None

    monkeypatch.setattr(gpt_handlers, "run_db", fake_run_db)
    await gpt_handlers.freeform_handler(update, context)
    assert entry["carbs_g"] == 12
    assert "Введите количество углеводов" in message.texts[0]


@pytest.mark.asyncio
async def test_freeform_handler_parse_command_negative(
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
        return {"sugar": None, "xe": None, "dose": None}

    async def fake_parse(text: str) -> dict[str, Any]:
        return {"action": "add_entry", "fields": {"sugar_before": -1}}

    monkeypatch.setattr(gpt_handlers, "smart_input", fake_smart_input)
    monkeypatch.setattr(gpt_handlers, "parse_command", fake_parse)
    await gpt_handlers.freeform_handler(update, context)
    assert "не могут быть отрицательными" in message.texts[0]


@pytest.mark.asyncio
async def test_freeform_handler_parse_command_bad_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage("cmd")
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

    async def fake_parse(text: str) -> dict[str, Any]:
        return {"action": "add_entry", "fields": None}

    monkeypatch.setattr(gpt_handlers, "smart_input", fake_smart_input)
    monkeypatch.setattr(gpt_handlers, "parse_command", fake_parse)
    await gpt_handlers.freeform_handler(update, context)
    assert message.texts == ["Не удалось распознать данные, попробуйте ещё раз."]


@pytest.mark.asyncio
async def test_freeform_handler_parse_command_valid_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage("entry")
    user_data: dict[str, Any] = {}
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data),
    )

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
    await gpt_handlers.freeform_handler(update, context)
    assert user_data["pending_entry"]["xe"] == 1
    assert "Расчёт завершён" in message.texts[0]


@pytest.mark.asyncio
async def test_freeform_handler_parse_command_bad_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage("entry")
    user_data: dict[str, Any] = {}
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data),
    )

    def fake_smart_input(text: str) -> dict[str, float | None]:
        return {"sugar": None, "xe": None, "dose": None}

    async def fake_parse(text: str) -> dict[str, Any]:
        return {
            "action": "add_entry",
            "fields": {"sugar_before": 5},
            "time": "bad",
        }

    monkeypatch.setattr(gpt_handlers, "smart_input", fake_smart_input)
    monkeypatch.setattr(gpt_handlers, "parse_command", fake_parse)
    await gpt_handlers.freeform_handler(update, context)
    assert "Неверный формат времени" in message.texts[0]


@pytest.mark.asyncio
async def test_freeform_handler_no_message() -> None:
    update = cast(
        Update,
        SimpleNamespace(message=None, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    await gpt_handlers.freeform_handler(update, context)
    assert cast(dict[str, Any], context.user_data) == {}


@pytest.mark.asyncio
async def test_freeform_handler_no_user() -> None:
    message = DummyMessage("text")
    update = cast(Update, SimpleNamespace(message=message, effective_user=None))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    await gpt_handlers.freeform_handler(update, context)
    assert message.texts == []


@pytest.mark.asyncio
async def test_freeform_handler_no_user_data() -> None:
    message = DummyMessage("text")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=None),
    )
    await gpt_handlers.freeform_handler(update, context)
    assert message.texts == []


@pytest.mark.asyncio
async def test_freeform_handler_no_text() -> None:
    message = DummyMessage(None)
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    await gpt_handlers.freeform_handler(update, context)
    assert message.texts == []
