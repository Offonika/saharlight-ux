from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.base import SchedulerNotRunningError
from telegram.ext import JobQueue

from services.api.app.diabetes.utils.jobs import _remove_jobs


async def dummy(_: object) -> None:
    pass


def test_jobs_remove() -> None:
    scheduler = BackgroundScheduler(paused=True)
    jq = JobQueue()
    jq.scheduler = scheduler

    jq.run_once(dummy, 0, name="reminder_42")
    jq.run_once(dummy, 0, name="reminder_42_after")
    jq.run_once(dummy, 0, name="reminder_42_snooze")
    jq.run_once(dummy, 0, name="reminder_999")

    removed = _remove_jobs(jq, "reminder_42")
    assert removed == 3
    assert not jq.get_jobs_by_name("reminder_42")
    assert jq.get_jobs_by_name("reminder_999")

    removed = _remove_jobs(jq, "reminder_42")
    assert removed == 0

    try:
        scheduler.shutdown(wait=False)
    except SchedulerNotRunningError:
        pass
    executor = getattr(jq, "executor", None) or getattr(jq, "_executor", None)
    try:
        executor.shutdown(wait=False)
    except AttributeError:
        pass
