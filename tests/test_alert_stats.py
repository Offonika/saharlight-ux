import datetime as dt
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from telegram.ext import CallbackContext

from services.api.app.diabetes.services.db import Base, Alert, User
import services.api.app.diabetes.handlers.alert_handlers as alert_handlers

if TYPE_CHECKING:
    from telegram import Update


class DummyMessage:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_alert_stats_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    alert_handlers.SessionLocal = TestSession

    class DummyDateTime(dt.datetime):
        @classmethod
        def now(
            cls, tz: dt.tzinfo | None = None
        ) -> "DummyDateTime":  # pragma: no cover - used for typing
            return fixed_now

    fixed_now = DummyDateTime(2024, 1, 10, tzinfo=dt.timezone.utc)

    @dataclass
    class DummyDateTimeModule:
        datetime: type[dt.datetime]
        timedelta: type[dt.timedelta]
        timezone: type[dt.timezone]

    monkeypatch.setattr(
        alert_handlers,
        "datetime",
        DummyDateTimeModule(
            DummyDateTime,
            dt.timedelta,
            dt.timezone,
        ),
    )

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(
            Alert(user_id=1, type="hypo", ts=fixed_now - dt.timedelta(days=1))
        )
        session.add(
            Alert(user_id=1, type="hyper", ts=fixed_now - dt.timedelta(days=2))
        )
        session.add(
            Alert(user_id=1, type="hyper", ts=fixed_now - dt.timedelta(days=8))
        )
        session.add(
            Alert(user_id=2, type="hypo", ts=fixed_now - dt.timedelta(days=1))
        )
        session.commit()

    msg = DummyMessage()

    @dataclass
    class DummyUser:
        id: int

    @dataclass
    class DummyUpdate:
        message: DummyMessage
        effective_user: DummyUser

    @dataclass
    class DummyContext:
        pass

    update = cast("Update", DummyUpdate(message=msg, effective_user=DummyUser(id=1)))
    context = cast(CallbackContext[Any, Any, Any, Any], DummyContext())

    await alert_handlers.alert_stats(update, context)
    assert msg.texts == ["За 7\u202Fдн.: гипо\u202F1, гипер\u202F1"]
