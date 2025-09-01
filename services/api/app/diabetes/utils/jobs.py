from __future__ import annotations

import inspect
from collections.abc import Callable, Coroutine, Iterable
from datetime import (
    datetime,
    time as dt_time,
    timedelta,
    timezone as dt_timezone,
    tzinfo,
)
from typing import Any, TYPE_CHECKING, TypeAlias, cast

from telegram.ext import ContextTypes, Job, JobQueue

CustomContext: TypeAlias = ContextTypes.DEFAULT_TYPE

if TYPE_CHECKING:
    DefaultJobQueue: TypeAlias = JobQueue[ContextTypes.DEFAULT_TYPE]
else:
    DefaultJobQueue = JobQueue

JobCallback = Callable[[CustomContext], Coroutine[Any, Any, object]]


def schedule_once(
    job_queue: DefaultJobQueue,
    callback: JobCallback,
    *,
    when: datetime | timedelta | float,
    data: dict[str, object] | None = None,
    name: str | None = None,
    timezone: tzinfo | None = None,
    job_kwargs: dict[str, object] | None = None,
) -> Job[CustomContext]:
    """Schedule ``callback`` to run once at ``when``.

    If ``job_queue.run_once`` supports a ``timezone`` argument, the job queue's
    timezone is forwarded automatically.  ``timezone`` can be provided
    explicitly; otherwise the timezone is derived from the job queue's
    application or scheduler.
    """
    if not inspect.iscoroutinefunction(callback):
        msg = "Job callback must be async"
        raise TypeError(msg)
    tz = (
        timezone
        or getattr(getattr(job_queue, "application", None), "timezone", None)
        or getattr(job_queue, "timezone", None)
        or getattr(
            getattr(getattr(job_queue, "application", None), "scheduler", None),
            "timezone",
            None,
        )
        or getattr(getattr(job_queue, "scheduler", None), "timezone", None)
        or dt_timezone.utc
    )

    if isinstance(when, datetime) and when.tzinfo is None:
        when = when.replace(tzinfo=tz)

    params: dict[str, Any] = {"when": when, "data": data, "name": name}
    sig = inspect.signature(job_queue.run_once)
    if "timezone" in sig.parameters:
        params["timezone"] = tz
    if job_kwargs is not None and "job_kwargs" in sig.parameters:
        params["job_kwargs"] = job_kwargs
    return job_queue.run_once(callback, **params)


def schedule_daily(
    job_queue: DefaultJobQueue,
    callback: JobCallback,
    *,
    time: dt_time,
    data: dict[str, object] | None = None,
    name: str | None = None,
    timezone: tzinfo | None = None,
    days: Iterable[int] | None = None,
    job_kwargs: dict[str, object] | None = None,
) -> Job[CustomContext]:
    """Schedule ``callback`` to run daily at ``time``.

    If ``job_queue.run_daily`` supports a ``timezone`` argument, the job
    queue's timezone is forwarded automatically. ``timezone`` can be provided
    explicitly; otherwise the timezone is derived from the job queue's
    application or scheduler.
    """
    if not inspect.iscoroutinefunction(callback):
        msg = "Job callback must be async"
        raise TypeError(msg)
    tz = (
        timezone
        or getattr(getattr(job_queue, "application", None), "timezone", None)
        or getattr(job_queue, "timezone", None)
        or getattr(
            getattr(getattr(job_queue, "application", None), "scheduler", None),
            "timezone",
            None,
        )
        or getattr(getattr(job_queue, "scheduler", None), "timezone", None)
        or dt_timezone.utc
    )

    if time.tzinfo is not None:
        now = datetime.now(time.tzinfo)
        dt = datetime.combine(now.date(), time, tzinfo=time.tzinfo)
        time = dt.astimezone(tz).time().replace(tzinfo=None)

    params: dict[str, Any] = {
        "time": time,
        "data": data,
        "name": name,
    }
    sig = inspect.signature(job_queue.run_daily)
    if "timezone" in sig.parameters:
        params["timezone"] = tz
    if days is not None and "days" in sig.parameters:
        params["days"] = tuple(days)
    if job_kwargs is not None and "job_kwargs" in sig.parameters:
        params["job_kwargs"] = job_kwargs
    return job_queue.run_daily(callback, **params)


def _remove_jobs(job_queue: DefaultJobQueue, name: str) -> int:
    """Best-effort removal of jobs from the queue.

    Tries ``job.remove()`` first, then falls back to direct scheduler
    removal, and finally schedules the job for removal. Returns the number of
    jobs processed.
    """
    removed = 0
    for job in job_queue.get_jobs_by_name(name):
        remover = cast(Callable[[], None] | None, getattr(job, "remove", None))
        if remover is not None:
            try:
                remover()
                removed += 1
                continue
            except Exception:  # pragma: no cover - defensive
                pass
        scheduler = getattr(job_queue, "scheduler", None)
        remove_job = (
            cast(Callable[[object], None] | None, getattr(scheduler, "remove_job", None))
            if scheduler is not None
            else None
        )
        job_id = getattr(job, "id", None)
        if remove_job is not None and job_id is not None:
            try:
                remove_job(job_id)
                removed += 1
                continue
            except Exception:  # pragma: no cover - defensive
                pass
        schedule_removal = cast(
            Callable[[], None] | None, getattr(job, "schedule_removal", None)
        )
        if schedule_removal is not None:
            schedule_removal()
            removed += 1
    return removed
