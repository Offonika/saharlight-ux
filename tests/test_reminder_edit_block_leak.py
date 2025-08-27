import json
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.api.app.diabetes.services.db import Base, User, Reminder, Entry
import services.api.app.diabetes.handlers.reminder_handlers as handlers
from services.api.app.diabetes.services.repository import commit
from tests.helpers import make_context, make_update


class DummyMessage:
    def __init__(self, data: str) -> None:
        self.web_app_data = SimpleNamespace(data=data)
        self.replies: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)


class DummyJobQueue:
    def run_daily(self, *a: Any, **k: Any) -> None:
        pass

    def run_repeating(self, *a: Any, **k: Any) -> None:
        pass

    def get_jobs_by_name(self, name: Any) -> None:
        return []


def _setup_db() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit
    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time="08:00", is_enabled=True))
        session.commit()
    return TestSession


@pytest.mark.asyncio
async def test_bad_input_does_not_create_entry() -> None:
    TestSession = _setup_db()
    msg = DummyMessage(json.dumps({"id": 1, "type": "sugar", "value": "bad"}))
    update = make_update(effective_message=msg, effective_user=SimpleNamespace(id=1))
    context = make_context(job_queue=DummyJobQueue())
    await handlers.reminder_webapp_save(update, context)
    assert msg.replies and "Неверный формат" in msg.replies[0]
    with TestSession() as session:
        assert session.query(Entry).count() == 0


@pytest.mark.asyncio
async def test_good_input_updates_and_ends() -> None:
    TestSession = _setup_db()
    msg = DummyMessage(json.dumps({"id": 1, "type": "sugar", "value": "09:30"}))
    update = make_update(effective_message=msg, effective_user=SimpleNamespace(id=1))
    context = make_context(job_queue=DummyJobQueue())
    await handlers.reminder_webapp_save(update, context)
    with TestSession() as session:
        rem = session.get(Reminder, 1)
        assert rem.time == "09:30"
        assert session.query(Entry).count() == 0
