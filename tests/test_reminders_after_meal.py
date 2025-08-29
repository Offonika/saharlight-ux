from collections.abc import Callable
from datetime import timedelta
from typing import Any, cast

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import services.api.app.diabetes.handlers.reminder_handlers as handlers
from services.api.app.diabetes.services.db import Base, Reminder, User as DbUser


class DummyJob:
    def __init__(
        self,
        callback: Callable[..., Any],
        when: timedelta,
        data: dict[str, Any],
        name: str,
    ) -> None:
        self.callback = callback
        self.when = when
        self.data = data
        self.name = name


class DummyJobQueue:
    def __init__(self) -> None:
        self.jobs: list[DummyJob] = []

    def run_once(
        self,
        callback: Callable[..., Any],
        when: timedelta,
        data: dict[str, Any] | None = None,
        name: str | None = None,
    ) -> DummyJob:
        job = DummyJob(callback, when, data or {}, name or "")
        self.jobs.append(job)
        return job


def make_session() -> sessionmaker[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_schedule_after_meal_single_reminder() -> None:
    TestSession = make_session()
    handlers.SessionLocal = TestSession
    with TestSession() as session:
        user = DbUser(telegram_id=1, thread_id="t")
        session.add(user)
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="after_meal",
                minutes_after=30,
                is_enabled=True,
                user=user,
            )
        )
        session.commit()
    dummy_queue = DummyJobQueue()
    job_queue = cast(handlers.DefaultJobQueue, dummy_queue)
    handlers.schedule_after_meal(1, job_queue)
    assert len(dummy_queue.jobs) == 1
    job = dummy_queue.jobs[0]
    assert job.callback is handlers.reminder_job
    assert job.when == timedelta(minutes=30)
    assert job.data == {"reminder_id": 1, "chat_id": 1}
    assert job.name == "reminder_1"


def test_schedule_after_meal_multiple_reminders() -> None:
    TestSession = make_session()
    handlers.SessionLocal = TestSession
    with TestSession() as session:
        user = DbUser(telegram_id=1, thread_id="t")
        session.add(user)
        session.add_all(
            [
                Reminder(
                    id=1,
                    telegram_id=1,
                    type="after_meal",
                    minutes_after=15,
                    is_enabled=True,
                    user=user,
                ),
                Reminder(
                    id=2,
                    telegram_id=1,
                    type="after_meal",
                    minutes_after=45,
                    is_enabled=True,
                    user=user,
                ),
            ]
        )
        session.commit()
    dummy_queue = DummyJobQueue()
    handlers.schedule_after_meal(1, cast(handlers.DefaultJobQueue, dummy_queue))
    assert len(dummy_queue.jobs) == 2
    jobs = {job.name: job for job in dummy_queue.jobs}
    job1 = jobs["reminder_1"]
    assert job1.when == timedelta(minutes=15)
    assert job1.data == {"reminder_id": 1, "chat_id": 1}
    job2 = jobs["reminder_2"]
    assert job2.when == timedelta(minutes=45)
    assert job2.data == {"reminder_id": 2, "chat_id": 1}


def test_schedule_after_meal_no_enabled_reminders() -> None:
    TestSession = make_session()
    handlers.SessionLocal = TestSession
    with TestSession() as session:
        user = DbUser(telegram_id=1, thread_id="t")
        session.add(user)
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="after_meal",
                minutes_after=30,
                is_enabled=False,
                user=user,
            )
        )
        session.commit()
    dummy_queue = DummyJobQueue()
    handlers.schedule_after_meal(1, cast(handlers.DefaultJobQueue, dummy_queue))
    assert not dummy_queue.jobs
