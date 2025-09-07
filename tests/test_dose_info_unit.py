from __future__ import annotations

import datetime
import os
from dataclasses import dataclass
from types import TracebackType
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")
import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
import services.api.app.diabetes.handlers.dose_calc as dose_calc
import services.api.app.diabetes.handlers.gpt_handlers as gpt_handlers

dose_handlers = dose_calc


class DummyMessage:
    def __init__(self, text: str) -> None:
        self.text: str = text
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


@dataclass
class DummyUser:
    id: int


@dataclass
class DummyUpdate:
    message: DummyMessage
    effective_user: DummyUser


@dataclass
class DummyContext:
    user_data: dict[str, Any]


@pytest.mark.asyncio
async def test_entry_without_dose_has_no_unit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pending_entry = {
        "telegram_id": 1,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
        "xe": 2.0,
    }
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        DummyContext(
            user_data={"pending_entry": pending_entry, "pending_fields": ["sugar"]}
        ),
    )
    message = DummyMessage("5.5")
    update = cast(Update, DummyUpdate(message=message, effective_user=DummyUser(id=1)))

    class DummySession(Session):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def __enter__(self) -> "DummySession":
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None:
            pass

        def add(self, instance: object, _warn: bool = False) -> None:
            self.entry = instance

    async def noop(*args: Any, **kwargs: Any) -> None:
        pass

    session_factory: sessionmaker[Session] = sessionmaker(class_=DummySession)
    monkeypatch.setattr(dose_handlers, "SessionLocal", session_factory)
    monkeypatch.setattr(dose_handlers, "commit", lambda session: None)
    monkeypatch.setattr(dose_handlers, "check_alert", noop)
    monkeypatch.setattr(dose_handlers, "build_main_keyboard", lambda: None)

    monkeypatch.setattr(gpt_handlers, "run_db", None)

    await dose_calc.freeform_handler(update, context)

    assert not context.user_data
    assert message.replies
    text = message.replies[0]
    assert "доза —" in text
    assert "Ед" not in text


@pytest.mark.asyncio
async def test_entry_without_sugar_has_placeholder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pending_entry = {
        "telegram_id": 1,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
    }
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        DummyContext(
            user_data={"pending_entry": pending_entry, "pending_fields": ["dose"]}
        ),
    )
    message = DummyMessage("5")
    update = cast(Update, DummyUpdate(message=message, effective_user=DummyUser(id=1)))

    class DummySession(Session):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def __enter__(self) -> "DummySession":
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None:
            pass

        def add(self, instance: object, _warn: bool = False) -> None:
            self.entry = instance

    async def noop(*args: Any, **kwargs: Any) -> None:
        pass

    session_factory: sessionmaker[Session] = sessionmaker(class_=DummySession)
    monkeypatch.setattr(dose_handlers, "SessionLocal", session_factory)
    monkeypatch.setattr(dose_handlers, "commit", lambda session: None)
    monkeypatch.setattr(dose_handlers, "check_alert", noop)
    monkeypatch.setattr(dose_handlers, "build_main_keyboard", lambda: None)

    monkeypatch.setattr(gpt_handlers, "run_db", None)

    await dose_calc.freeform_handler(update, context)

    assert not context.user_data
    assert message.replies
    text = message.replies[0]
    assert "сахар —" in text
    assert "ммоль/л" not in text
