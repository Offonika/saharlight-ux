import pytest
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from diabetes.db import Base, User, Reminder, ReminderLog
import diabetes.reminder_handlers as handlers
from diabetes.common_handlers import commit_session


class DummyMessage:
    def __init__(self):
        self.texts = []

    async def reply_text(self, text, **kwargs):
        self.texts.append(text)


class DummyBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, chat_id, text, **kwargs):
        self.messages.append((chat_id, text, kwargs))


class DummyJob:
    def __init__(self, callback, data, name):
        self.callback = callback
        self.data = data
        self.name = name
        self.removed = False

    def schedule_removal(self):
        self.removed = True


class DummyJobQueue:
    def __init__(self):
        self.jobs = []

    def run_daily(self, callback, time, data=None, name=None):
        self.jobs.append(DummyJob(callback, data, name))

    def run_repeating(self, callback, interval, data=None, name=None):
        self.jobs.append(DummyJob(callback, data, name))

    def run_once(self, callback, when, data=None, name=None):
        self.jobs.append(DummyJob(callback, data, name))

    def get_jobs_by_name(self, name):
        return [j for j in self.jobs if j.name == name]


@pytest.mark.asyncio
async def test_create_update_delete_reminder(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    job_queue = DummyJobQueue()

    msg = DummyMessage()
    update = SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(args=["sugar", "23:00"], job_queue=job_queue)
    await handlers.add_reminder(update, context)
    assert "Сохранено" in msg.texts[0]

    with TestSession() as session:
        rems = session.query(Reminder).all()
        assert len(rems) == 1
        rid = rems[0].id

    msg2 = DummyMessage()
    update2 = SimpleNamespace(message=msg2, effective_user=SimpleNamespace(id=1))
    context2 = SimpleNamespace(args=[str(rid), "sugar", "6"], job_queue=job_queue)
    await handlers.add_reminder(update2, context2)
    with TestSession() as session:
        rem = session.get(Reminder, rid)
        assert rem.interval_hours == 6

    msg3 = DummyMessage()
    update3 = SimpleNamespace(message=msg3, effective_user=SimpleNamespace(id=1))
    context3 = SimpleNamespace(args=[str(rid)], job_queue=job_queue)
    await handlers.delete_reminder(update3, context3)
    with TestSession() as session:
        assert session.query(Reminder).count() == 0


@pytest.mark.asyncio
async def test_add_reminder_missing_value(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time="23:00"))
        session.commit()

    msg = DummyMessage()
    update = SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(args=["1", "sugar"], job_queue=DummyJobQueue())

    result = await handlers.add_reminder(update, context)

    assert result is None
    assert msg.texts == ["Формат: /addreminder [id] <type> <time|interval>"]


@pytest.mark.asyncio
async def test_trigger_job_logs(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time="23:00"))
        session.commit()

    job_queue = DummyJobQueue()
    with TestSession() as session:
        rem_db = session.get(Reminder, 1)
        rem = Reminder(
            id=rem_db.id,
            telegram_id=rem_db.telegram_id,
            type=rem_db.type,
            time=rem_db.time,
        )
    handlers.schedule_reminder(rem, job_queue)
    bot = DummyBot()
    context = SimpleNamespace(
        bot=bot,
        job=SimpleNamespace(data={"reminder_id": 1, "chat_id": 1}),
        job_queue=job_queue,
    )
    await handlers.reminder_job(context)
    assert bot.messages[0][1].startswith("Замерить сахар")
    with TestSession() as session:
        log = session.query(ReminderLog).first()
        assert log.action == "trigger"
