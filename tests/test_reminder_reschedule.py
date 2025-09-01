from __future__ import annotations

from datetime import time as dt_time
from types import SimpleNamespace
from typing import Callable
from zoneinfo import ZoneInfo

from services.api.app.diabetes.handlers import reminder_handlers, reminder_jobs


class DummyJob:
    def __init__(
        self, scheduler: "DummyScheduler", *, id: str, name: str, run_time: dt_time
    ) -> None:
        self._scheduler = scheduler
        self.id = id
        self.name = name
        self.run_time = run_time

    def remove(self) -> None:
        self._scheduler.jobs = [j for j in self._scheduler.jobs if j.id != self.id]

    def schedule_removal(self) -> None:
        self.remove()


class DummyScheduler:
    def __init__(self, tz: ZoneInfo) -> None:
        self.timezone = tz
        self.jobs: list[DummyJob] = []

    def add_job(
        self,
        func: Callable[..., object],
        *,
        trigger: str,
        id: str,
        name: str,
        replace_existing: bool,
        timezone: ZoneInfo,
        kwargs: dict[str, object],
        **params: object,
    ) -> DummyJob:
        if replace_existing:
            self.jobs = [j for j in self.jobs if j.id != id]
        run_time = dt_time(int(params["hour"]), int(params["minute"]))
        job = DummyJob(self, id=id, name=name, run_time=run_time)
        self.jobs.append(job)
        return job

    def remove_job(self, job_id: str) -> None:
        self.jobs = [j for j in self.jobs if j.id != job_id]


class DummyJobQueue:
    def __init__(self) -> None:
        tz = ZoneInfo("UTC")
        self.scheduler = DummyScheduler(tz)
        self.application = SimpleNamespace(timezone=tz, scheduler=self.scheduler)

    def get_jobs_by_name(self, name: str) -> list[DummyJob]:
        return [j for j in self.scheduler.jobs if j.name == name]


def test_editing_reminder_replaces_job() -> None:
    job_queue = DummyJobQueue()
    rem = SimpleNamespace(
        id=1,
        telegram_id=1,
        type="sugar",
        time=dt_time(8, 0),
        interval_hours=None,
        interval_minutes=None,
        minutes_after=None,
        kind="at_time",
        is_enabled=True,
        days_mask=0,
    )
    user = SimpleNamespace(timezone="UTC")

    reminder_jobs.schedule_reminder(rem, job_queue, user)
    assert [j.run_time for j in job_queue.get_jobs_by_name("reminder_1")] == [
        dt_time(8, 0)
    ]

    rem.time = dt_time(9, 0)
    reminder_jobs.schedule_reminder(rem, job_queue, user)
    jobs = job_queue.get_jobs_by_name("reminder_1")
    assert len(jobs) == 1
    assert jobs[0].run_time == dt_time(9, 0)


def test_reschedule_job_helper_recreates_job() -> None:
    job_queue = DummyJobQueue()
    rem = SimpleNamespace(
        id=1,
        telegram_id=1,
        type="sugar",
        time=dt_time(8, 0),
        interval_hours=None,
        interval_minutes=None,
        minutes_after=None,
        kind="at_time",
        is_enabled=True,
        days_mask=0,
    )
    user = SimpleNamespace(timezone="UTC")

    reminder_jobs.schedule_reminder(rem, job_queue, user)
    assert [j.run_time for j in job_queue.get_jobs_by_name("reminder_1")] == [
        dt_time(8, 0)
    ]

    job_queue.scheduler.add_job(
        lambda: None,
        trigger="cron",
        id="reminder_1_snooze",
        name="reminder_1_snooze",
        replace_existing=False,
        timezone=job_queue.scheduler.timezone,
        kwargs={},
        hour=0,
        minute=0,
    )
    assert job_queue.get_jobs_by_name("reminder_1_snooze")

    rem.time = dt_time(9, 30)
    reminder_handlers._reschedule_job(job_queue, rem, user)
    jobs = job_queue.get_jobs_by_name("reminder_1")
    assert len(jobs) == 1
    assert jobs[0].run_time == dt_time(9, 30)
    assert not job_queue.get_jobs_by_name("reminder_1_snooze")


def test_reschedule_job_helper_handles_jobs_without_remove() -> None:
    job_queue = DummyJobQueue()
    rem = SimpleNamespace(
        id=1,
        telegram_id=1,
        type="sugar",
        time=dt_time(8, 0),
        interval_hours=None,
        interval_minutes=None,
        minutes_after=None,
        kind="at_time",
        is_enabled=True,
        days_mask=0,
    )
    user = SimpleNamespace(timezone="UTC")

    reminder_jobs.schedule_reminder(rem, job_queue, user)
    job = job_queue.get_jobs_by_name("reminder_1")[0]
    setattr(job, "remove", None)

    rem.time = dt_time(9, 45)
    reminder_handlers._reschedule_job(job_queue, rem, user)
    jobs = job_queue.get_jobs_by_name("reminder_1")
    assert len(jobs) == 1
    assert jobs[0].run_time == dt_time(9, 45)
