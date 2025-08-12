import json
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from diabetes.services.db import Base, User, Reminder, Entry
import diabetes.handlers.reminder_handlers as handlers
from diabetes.handlers.common_handlers import commit_session


class DummyMessage:
    def __init__(self, data: str):
        self.web_app_data = SimpleNamespace(data=data)
        self.replies: list[str] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


class DummyJobQueue:
    def run_daily(self, *a, **k):
        pass

    def run_repeating(self, *a, **k):
        pass

    def get_jobs_by_name(self, name):
        return []


def _setup_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session
    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time="08:00", is_enabled=True))
        session.commit()
    return TestSession


@pytest.mark.asyncio
async def test_bad_input_does_not_create_entry():
    TestSession = _setup_db()
    msg = DummyMessage(json.dumps({"id": 1, "type": "sugar", "value": "bad"}))
    update = SimpleNamespace(effective_message=msg, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(job_queue=DummyJobQueue())
    await handlers.reminder_webapp_save(update, context)
    assert msg.replies and "Неверный формат" in msg.replies[0]
    with TestSession() as session:
        assert session.query(Entry).count() == 0


@pytest.mark.asyncio
async def test_good_input_updates_and_ends():
    TestSession = _setup_db()
    msg = DummyMessage(json.dumps({"id": 1, "type": "sugar", "value": "09:30"}))
    update = SimpleNamespace(effective_message=msg, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(job_queue=DummyJobQueue())
    await handlers.reminder_webapp_save(update, context)
    with TestSession() as session:
        rem = session.get(Reminder, 1)
        assert rem.time == "09:30"
        assert session.query(Entry).count() == 0
