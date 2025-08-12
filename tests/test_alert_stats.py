import datetime
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.api.app.diabetes.services.db import Base, Alert, User
import services.api.app.diabetes.handlers.alert_handlers as alert_handlers

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import CallbackContext


class DummyMessage:
    def __init__(self) -> None:
        self.texts: list[str] = []

    async def reply_text(self, text: str) -> None:
        self.texts.append(text)


@pytest.mark.asyncio
async def test_alert_stats_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    alert_handlers.SessionLocal = TestSession

    fixed_now = datetime.datetime(2024, 1, 10, tzinfo=datetime.timezone.utc)

    class DummyDateTime(datetime.datetime):
        @classmethod
        def now(
            cls, tz: datetime.tzinfo | None = None
        ) -> datetime.datetime:  # pragma: no cover - used for typing
            return fixed_now

    @dataclass
    class DummyDateTimeModule:
        datetime: type[datetime.datetime]
        timedelta: type[datetime.timedelta]
        timezone: type[datetime.timezone]

    monkeypatch.setattr(
        alert_handlers,
        "datetime",
        DummyDateTimeModule(
            DummyDateTime,
            datetime.timedelta,
            datetime.timezone,
        ),
    )

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(
            Alert(user_id=1, type="hypo", ts=fixed_now - datetime.timedelta(days=1))
        )
        session.add(
            Alert(user_id=1, type="hyper", ts=fixed_now - datetime.timedelta(days=2))
        )
        session.add(
            Alert(user_id=1, type="hyper", ts=fixed_now - datetime.timedelta(days=8))
        )
        session.add(
            Alert(user_id=2, type="hypo", ts=fixed_now - datetime.timedelta(days=1))
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
    context = cast("CallbackContext[Any, Any, Any, Any]", DummyContext())

    await alert_handlers.alert_stats(update, context)
    assert msg.texts == ["За 7\u202Fдн.: гипо\u202F1, гипер\u202F1"]

