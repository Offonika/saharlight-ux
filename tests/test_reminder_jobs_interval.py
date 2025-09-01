from __future__ import annotations

from datetime import timedelta
from typing import Any

from services.api.app.diabetes.handlers import reminder_jobs
from services.api.app.diabetes.services.db import Reminder, User as DbUser


class DummyJob:
    def __init__(self, name: str, interval: timedelta) -> None:
        self.name = name
        self.interval = interval


class DummyJobQueue:
    def __init__(self) -> None:
        self.jobs: list[DummyJob] = []

    def run_daily(
        self, *args: Any, **kwargs: Any
    ) -> None:  # pragma: no cover - shouldn't happen
        raise AssertionError("run_daily should not be called")

    def run_repeating(
        self,
        callback: Any,
        *,
        interval: timedelta,
        data: dict[str, Any] | None = None,
        name: str | None = None,
        job_kwargs: dict[str, Any] | None = None,
    ) -> DummyJob:
        job = DummyJob(name or "", interval)
        self.jobs.append(job)
        return job

    def get_jobs_by_name(self, name: str) -> list[DummyJob]:
        return [job for job in self.jobs if job.name == name]


def test_schedule_reminder_interval_hours() -> None:
    job_queue = DummyJobQueue()
    user = DbUser(telegram_id=1, thread_id="t", timezone="UTC")
    rem = Reminder(
        id=1,
        telegram_id=1,
        type="sugar",
        interval_hours=2,
        is_enabled=True,
    )
    reminder_jobs.schedule_reminder(rem, job_queue, user)
    jobs = job_queue.get_jobs_by_name("reminder_1")
    assert len(jobs) == 1
    job = jobs[0]
    assert job.interval == timedelta(minutes=120)
