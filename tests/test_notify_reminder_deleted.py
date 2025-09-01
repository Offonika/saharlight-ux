from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import SchedulerNotRunningError
from telegram.ext import JobQueue

from services.api.app import reminder_events


async def dummy(_: object) -> None:
    pass


def test_notify_reminder_deleted_removes_jobs() -> None:
    scheduler = BackgroundScheduler(paused=True)
    jq = JobQueue()
    jq.scheduler = scheduler
    reminder_events.register_job_queue(jq)

    jq.run_once(dummy, 0, name="reminder_42")
    jq.run_once(dummy, 0, name="reminder_42_after")
    jq.run_once(dummy, 0, name="reminder_42_snooze")
    jq.run_once(dummy, 0, name="reminder_999")

    reminder_events.notify_reminder_deleted(42)

    assert not jq.get_jobs_by_name("reminder_42")
    assert not jq.get_jobs_by_name("reminder_42_after")
    assert not jq.get_jobs_by_name("reminder_42_snooze")
    assert jq.get_jobs_by_name("reminder_999")

    reminder_events.register_job_queue(None)

    try:
        scheduler.shutdown(wait=False)
    except SchedulerNotRunningError:
        pass
    executor = getattr(jq, "executor", None) or getattr(jq, "_executor", None)
    try:
        executor.shutdown(wait=False)
    except AttributeError:
        pass
