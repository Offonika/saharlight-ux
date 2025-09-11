from types import SimpleNamespace, TracebackType
from typing import Any, cast

import pytest
from telegram import Message, Update
from telegram.ext import CallbackContext
from sqlalchemy.orm import Session, sessionmaker

from services.api.app.diabetes.handlers import UserData, gpt_handlers


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.texts: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.kwargs.append(kwargs)


async def _noop_alert(
    update: Update, context: CallbackContext[Any, Any, Any, Any], sugar: float
) -> None:
    return None


class DummySession:
    def __enter__(self) -> "DummySession":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        pass

    def add(self, obj: Any) -> None:
        pass


def session_factory() -> Session:
    return cast(Session, DummySession())


SESSION_FACTORY = cast(sessionmaker[Session], session_factory)


@pytest.mark.asyncio
async def test_handle_pending_entry_nan() -> None:
    message = DummyMessage("nan")
    update = cast(Update, SimpleNamespace(message=cast(Message, message)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    user_data: dict[str, Any] = {"pending_entry": {}, "pending_fields": ["xe"]}

    handled = await gpt_handlers._handle_pending_entry(
        "nan",
        cast(UserData, user_data),
        cast(Message, message),
        update,
        context,
        1,
        SessionLocal=SESSION_FACTORY,
        commit=lambda s: None,
        check_alert=_noop_alert,
        menu_keyboard=None,
    )
    assert handled is True
    assert user_data["pending_entry"] == {}
    assert message.texts == ["Введите число ХЕ."]


@pytest.mark.asyncio
async def test_handle_pending_entry_inf() -> None:
    message = DummyMessage("inf")
    update = cast(Update, SimpleNamespace(message=cast(Message, message)))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    user_data: dict[str, Any] = {"pending_entry": {}, "pending_fields": ["dose"]}

    handled = await gpt_handlers._handle_pending_entry(
        "inf",
        cast(UserData, user_data),
        cast(Message, message),
        update,
        context,
        1,
        SessionLocal=SESSION_FACTORY,
        commit=lambda s: None,
        check_alert=_noop_alert,
        menu_keyboard=None,
    )
    assert handled is True
    assert user_data["pending_entry"] == {}
    assert message.texts == ["Введите дозу инсулина числом."]
