import json
from typing import Any
from unittest.mock import MagicMock

import pytest
from telegram import Update, User
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.reminder_handlers as reminder_handlers
from services.api.app.config import settings
from services.api.app.diabetes.utils.helpers import INVALID_TIME_MSG


class DummyMessage:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.kwargs.append(kwargs)


class DummyWebAppData:
    def __init__(self, data: str) -> None:
        self.data = data


class DummyWebAppMessage(DummyMessage):
    def __init__(self, data: str) -> None:
        super().__init__()
        self.web_app_data = DummyWebAppData(data)

def make_user(user_id: int) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = user_id
    return user


def make_update(**kwargs: Any) -> MagicMock:
    update = MagicMock(spec=Update)
    for key, value in kwargs.items():
        setattr(update, key, value)
    return update


def make_context(**kwargs: Any) -> MagicMock:
    context = MagicMock(spec=CallbackContext)
    for key, value in kwargs.items():
        setattr(context, key, value)
    return context


@pytest.mark.asyncio
async def test_add_reminder_fewer_args() -> None:
    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    context = make_context(args=["sugar"])

    await reminder_handlers.add_reminder(update, context)

    assert message.texts == ["Использование: /addreminder <type> <value>"]


@pytest.mark.asyncio
async def test_add_reminder_sugar_invalid_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    context = make_context(args=["sugar", "ab:cd"])

    parse_mock = MagicMock(side_effect=ValueError)
    monkeypatch.setattr(reminder_handlers, "parse_time_interval", parse_mock)

    await reminder_handlers.add_reminder(update, context)

    assert message.texts == [INVALID_TIME_MSG]
    parse_mock.assert_called_once_with("ab:cd")


@pytest.mark.asyncio
async def test_add_reminder_sugar_non_numeric_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    context = make_context(args=["sugar", "abc"])

    parse_mock = MagicMock()
    monkeypatch.setattr(reminder_handlers, "parse_time_interval", parse_mock)

    await reminder_handlers.add_reminder(update, context)

    assert message.texts == ["Интервал должен быть числом."]
    parse_mock.assert_not_called()


@pytest.mark.asyncio
async def test_add_reminder_unknown_type() -> None:
    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    context = make_context(args=["unknown", "1"])

    await reminder_handlers.add_reminder(update, context)

    assert message.texts == ["Неизвестный тип напоминания."]


@pytest.mark.asyncio
async def test_add_reminder_valid_type(monkeypatch: pytest.MonkeyPatch) -> None:
    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    context = make_context(args=["sugar", "2"], job_queue=None)

    async def fake_run_db(*args: Any, **kwargs: Any) -> tuple[str, None, int, int]:
        return "ok", None, 5, 1

    monkeypatch.setattr(reminder_handlers, "run_db", fake_run_db)
    monkeypatch.setattr(reminder_handlers, "_describe", lambda *a, **k: "desc")

    await reminder_handlers.add_reminder(update, context)

    assert message.texts == ["Сохранено: desc"]


@pytest.mark.asyncio
async def test_reminder_webapp_save_unknown_type() -> None:
    message = DummyWebAppMessage(json.dumps({"type": "bad", "value": "10:00"}))
    update = make_update(effective_message=message, effective_user=make_user(1))
    context = make_context()

    await reminder_handlers.reminder_webapp_save(update, context)

    assert message.texts == ["Неизвестный тип напоминания."]


@pytest.mark.parametrize(
    "base_url",
    [
        "https://example.com",
        "https://example.com/",
        "https://example.com/ui",
        "https://example.com/ui/",
    ],
)
def test_build_webapp_url(monkeypatch: pytest.MonkeyPatch, base_url: str) -> None:
    monkeypatch.setattr(settings, "webapp_url", base_url)
    url = reminder_handlers.build_webapp_url("/ui/reminders")
    assert url == "https://example.com/ui/reminders"
    assert "//" not in url.split("://", 1)[1]
