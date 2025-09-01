from __future__ import annotations

from datetime import time as dt_time
from types import SimpleNamespace
from typing import Callable
from zoneinfo import ZoneInfo

from services.api.app.diabetes.handlers import reminder_handlers, reminder_jobs


class DummyJob:
    def __init__(self, queue: "DummyJobQueue", name: str | None, run_time: dt_time) -> None:
        self._queue = queue
        self.name = name
        self.run_time = run_time
        self.id = name

    def remove(self) -> None:
        self._queue._jobs.remove(self)

    def schedule_removal(self) -> None:
        self.remove()


class DummyJobQueue:
    def __init__(self) -> None:
        tz = ZoneInfo("UTC")
        self._jobs: list[DummyJob] = []

        def remove_job(job_id: str) -> None:
            for job in list(self._jobs):
                if getattr(job, "id", None) == job_id:
                    self._jobs.remove(job)

        scheduler = SimpleNamespace(timezone=tz, remove_job=remove_job)
        self.application = SimpleNamespace(timezone=tz, scheduler=scheduler)
        self.scheduler = scheduler

    def run_daily(
        self,
        callback: Callable[..., object],
        *,
        time: dt_time,
        data: dict[str, object] | None = None,
        name: str | None = None,
        timezone: ZoneInfo | None = None,
        days: tuple[int, ...] | None = None,
    ) -> DummyJob:
        job = DummyJob(self, name, time)
        self._jobs.append(job)
        return job

    def get_jobs_by_name(self, name: str) -> list[DummyJob]:
        return [j for j in self._jobs if j.name == name]


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
    assert [j.run_time for j in job_queue.get_jobs_by_name("reminder_1")] == [dt_time(8, 0)]

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
    assert [j.run_time for j in job_queue.get_jobs_by_name("reminder_1")] == [dt_time(8, 0)]

    rem.time = dt_time(9, 30)
    reminder_handlers._reschedule_job(job_queue, rem, user)
    jobs = job_queue.get_jobs_by_name("reminder_1")
    assert len(jobs) == 1
    assert jobs[0].run_time == dt_time(9, 30)


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
