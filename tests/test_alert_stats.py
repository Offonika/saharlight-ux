import datetime
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.api.app.diabetes.services.db import Base, Alert, User
import services.api.app.diabetes.handlers.alert_handlers as alert_handlers


class DummyMessage:
    def __init__(self):
        self.texts: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)


@pytest.mark.asyncio
async def test_alert_stats_counts(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    alert_handlers.SessionLocal = TestSession

    fixed_now = datetime.datetime(2024, 1, 10, tzinfo=datetime.timezone.utc)

    class DummyDateTime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    monkeypatch.setattr(
        alert_handlers,
        "datetime",
        SimpleNamespace(
            datetime=DummyDateTime,
            timedelta=datetime.timedelta,
            timezone=datetime.timezone,
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
    update = SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace()

    await alert_handlers.alert_stats(update, context)
    assert msg.texts == ["За 7\u202Fдн.: гипо\u202F1, гипер\u202F1"]

