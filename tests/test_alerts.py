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
        session.add(Profile(telegram_id=1, low_threshold=4, high_threshold=8))
        session.add(User(telegram_id=2, thread_id="t2"))
        session.add(Profile(telegram_id=2, low_threshold=4, high_threshold=8))
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
        session.add(Profile(telegram_id=1, low_threshold=4, high_threshold=8))
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
        session.add(Profile(telegram_id=1, low_threshold=4, high_threshold=8))
        session.commit()

    job_queue = DummyJobQueue()
    handlers.evaluate_sugar(1, 3, job_queue)
    assert job_queue.jobs

    handlers.evaluate_sugar(1, 5, job_queue)
    with TestSession() as session:
        alert = session.query(Alert).filter_by(user_id=1).first()
        assert alert.resolved
    assert job_queue.jobs[0].removed
