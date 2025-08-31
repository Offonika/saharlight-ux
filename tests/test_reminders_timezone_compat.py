from __future__ import annotations

from datetime import time, timedelta
from types import SimpleNamespace
from typing import Any, cast
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


from services.api.app.diabetes.services.db import (
    Base,
    Reminder,
    User as DbUser,
)
import services.api.app.diabetes.handlers.reminder_handlers as handlers
from services.api.app.diabetes.handlers.reminder_jobs import (
    DefaultJobQueue,
    schedule_reminder,
)
from services.api.app.diabetes.services.repository import commit
from tests.test_reminders import (
    DummyBot,
    DummyCallbackQuery,
    DummyMessage,
    make_context,
    make_update,
    make_user,
)


class DummyJob:
    def __init__(self, name: str) -> None:
        self.name = name
        self.removed = False

    def schedule_removal(self) -> None:
        self.removed = True


class BaseQueue:
    def __init__(self, tz: ZoneInfo) -> None:
        self.application = SimpleNamespace(timezone=tz)
        self.scheduler = SimpleNamespace(timezone=tz)
        self.jobs: list[DummyJob] = []
        self.last_timezone: ZoneInfo | None = None
        self.last_time: time | None = None

    def get_jobs_by_name(self, name: str) -> list[DummyJob]:
        return [j for j in self.jobs if j.name == name]


class QueueV20(BaseQueue):
    def run_daily(
        self,
        callback: Any,
        time: time,
        data: dict[str, Any] | None = None,
        name: str | None = None,
        timezone: ZoneInfo | None = None,
    ) -> DummyJob:
        self.last_timezone = timezone
        self.last_time = time
        job = DummyJob(name or "")
        self.jobs.append(job)
        return job

    def run_once(
        self,
        callback: Any,
        when: timedelta,
        data: dict[str, Any] | None = None,
        name: str | None = None,
        timezone: ZoneInfo | None = None,
    ) -> DummyJob:
        self.last_timezone = timezone
        job = DummyJob(name or "")
        self.jobs.append(job)
        return job


class QueueV21(BaseQueue):
    def run_daily(
        self,
        callback: Any,
        time: time,
        data: dict[str, Any] | None = None,
        name: str | None = None,
    ) -> DummyJob:
        self.last_timezone = None
        self.last_time = time
        job = DummyJob(name or "")
        self.jobs.append(job)
        return job

    def run_once(
        self,
        callback: Any,
        when: timedelta,
        data: dict[str, Any] | None = None,
        name: str | None = None,
    ) -> DummyJob:
        self.last_timezone = None
        job = DummyJob(name or "")
        self.jobs.append(job)
        return job


@pytest.mark.parametrize(
    "queue_cls, expects_tz",
    [(QueueV20, True), (QueueV21, False)],
)
def test_schedule_reminder_respects_queue_timezone(
    queue_cls: type[BaseQueue], expects_tz: bool
) -> None:
    user = DbUser(telegram_id=1, thread_id="t", timezone="Europe/Paris")
    rem = Reminder(
        id=1,
        telegram_id=1,
        type="sugar",
        time=time(9, 0),
        is_enabled=True,
        user=user,
    )
    tz = ZoneInfo("UTC")
    job_queue = cast(DefaultJobQueue, queue_cls(tz))
    schedule_reminder(rem, job_queue, user)
    assert job_queue.last_time == time(8, 0)
    if expects_tz:
        assert job_queue.last_timezone == tz
    else:
        assert job_queue.last_timezone is None


@pytest.mark.parametrize(
    "queue_cls, expects_tz",
    [(QueueV20, True), (QueueV21, False)],
)
def test_schedule_after_meal_uses_queue_timezone(
    queue_cls: type[BaseQueue], expects_tz: bool
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="after_meal",
                minutes_after=30,
                is_enabled=True,
            )
        )
        session.commit()
    tz = ZoneInfo("UTC")
    job_queue = cast(DefaultJobQueue, queue_cls(tz))
    handlers.schedule_after_meal(1, job_queue)
    assert job_queue.jobs
    if expects_tz:
        assert job_queue.last_timezone == tz
    else:
        assert job_queue.last_timezone is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "queue_cls, expects_tz",
    [(QueueV20, True), (QueueV21, False)],
)
async def test_snooze_callback_uses_queue_timezone(
    queue_cls: type[BaseQueue], expects_tz: bool
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit
    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time=time(8, 0)))
        session.commit()
    query = DummyCallbackQuery("remind_snooze:1:15", DummyMessage())
    update = make_update(callback_query=query, effective_user=make_user(1))
    job_queue = cast(DefaultJobQueue, queue_cls(ZoneInfo("UTC")))
    context = make_context(job_queue=job_queue, bot=DummyBot())
    await handlers.reminder_callback(update, context)
    assert job_queue.jobs
    if expects_tz:
        assert job_queue.last_timezone == ZoneInfo("UTC")
    else:
        assert job_queue.last_timezone is None
