import pytest
from typing import Any
from unittest.mock import MagicMock

from telegram import Update, User
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.reminder_handlers as reminder_handlers
from services.api.app.diabetes.utils.helpers import INVALID_TIME_MSG


class DummyMessage:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.kwargs.append(kwargs)


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
