import pytest
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from diabetes.db import Base, User, Profile, Alert
import diabetes.alert_handlers as handlers
from diabetes.common_handlers import commit_session


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

    def run_once(self, callback, when, data=None, name=None):
        self.jobs.append(DummyJob(callback, data, name))

    def get_jobs_by_name(self, name):
        return [j for j in self.jobs if j.name == name]


@pytest.mark.asyncio
async def test_threshold_evaluation():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t1"))
        session.add(Profile(telegram_id=1, low_threshold=4, high_threshold=8, sos_alerts_enabled=True))
        session.add(User(telegram_id=2, thread_id="t2"))
        session.add(Profile(telegram_id=2, low_threshold=4, high_threshold=8, sos_alerts_enabled=True))
        session.commit()

    job_queue_low = DummyJobQueue()
    handlers.evaluate_sugar(1, 3, job_queue_low)
    with TestSession() as session:
        alert = session.query(Alert).filter_by(user_id=1).first()
        assert alert.type == "low"
    assert job_queue_low.get_jobs_by_name("alert_1")

    job_queue_high = DummyJobQueue()
    handlers.evaluate_sugar(2, 9, job_queue_high)
    with TestSession() as session:
        alert2 = session.query(Alert).filter_by(user_id=2).first()
        assert alert2.type == "high"
    assert job_queue_high.get_jobs_by_name("alert_2")


@pytest.mark.asyncio
async def test_repeat_logic():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Profile(telegram_id=1, low_threshold=4, high_threshold=8, sos_alerts_enabled=True))
        session.commit()

    job_queue = DummyJobQueue()
    handlers.evaluate_sugar(1, 3, job_queue)

    for i in range(1, 4):
        context = SimpleNamespace(job=SimpleNamespace(data={"user_id": 1, "count": i}), job_queue=job_queue)
        await handlers.alert_job(context)

    assert len(job_queue.jobs) == 3


@pytest.mark.asyncio
async def test_normal_reading_resolves_alert():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.add(Profile(telegram_id=1, low_threshold=4, high_threshold=8, sos_alerts_enabled=True))
        session.commit()

    job_queue = DummyJobQueue()
    handlers.evaluate_sugar(1, 3, job_queue)
    assert job_queue.jobs

    handlers.evaluate_sugar(1, 5, job_queue)
    with TestSession() as session:
        alert = session.query(Alert).filter_by(user_id=1).first()
        assert alert.resolved
    assert job_queue.jobs[0].removed


@pytest.mark.asyncio
async def test_three_alerts_notify(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit_session = commit_session

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t1"))
        session.add(Profile(
            telegram_id=1,
            low_threshold=4,
            high_threshold=8,
            sos_contact="2",
            sos_alerts_enabled=True,
        ))
        session.commit()

    class DummyBot:
        def __init__(self):
            self.sent = []

        async def send_message(self, chat_id, text):
            self.sent.append((chat_id, text))

    update = SimpleNamespace(effective_user=SimpleNamespace(id=1, first_name="Ivan"))
    context = SimpleNamespace(bot=DummyBot())
    async def fake_get_coords_and_link():
        return ("0,0", "link")

    monkeypatch.setattr(handlers, "get_coords_and_link", fake_get_coords_and_link)

    for _ in range(2):
        await handlers.check_alert(update, context, 3)
    assert context.bot.sent == []
    await handlers.check_alert(update, context, 3)
    assert len(context.bot.sent) == 2
    assert context.bot.sent[0][0] == 1
    assert context.bot.sent[1][0] == "2"
    with TestSession() as session:
        alerts = session.query(Alert).all()
        assert all(a.resolved for a in alerts)
