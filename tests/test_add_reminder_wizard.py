import json
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from diabetes.services.db import Base, User, Reminder
import diabetes.handlers.reminder_handlers as handlers
from diabetes.handlers.common_handlers import commit_session


class DummyMessage:
    def __init__(self, data: str):
        self.web_app_data = SimpleNamespace(data=data)
        self.replies: list[str] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


class DummyJobQueue:
    def __init__(self):
        self.jobs = []

    def run_daily(self, *args, **kwargs):
        pass

    def run_repeating(self, *args, **kwargs):
        pass

    def get_jobs_by_name(self, name):
        return []


@pytest.mark.asyncio
async def test_webapp_save_creates_reminder(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    msg = DummyMessage(json.dumps({"type": "sugar", "value": "08:00"}))
    update = SimpleNamespace(effective_message=msg, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(job_queue=DummyJobQueue())
    await handlers.reminder_webapp_save(update, context)

    with TestSession() as session:
        rem = session.query(Reminder).first()
        assert rem and rem.time == "08:00"


@pytest.mark.asyncio
async def test_webapp_save_creates_interval(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    msg = DummyMessage(json.dumps({"type": "sugar", "value": "2h"}))
    update = SimpleNamespace(effective_message=msg, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(job_queue=DummyJobQueue())
    await handlers.reminder_webapp_save(update, context)

    with TestSession() as session:
        rem = session.query(Reminder).first()
        assert rem and rem.interval_hours == 2
