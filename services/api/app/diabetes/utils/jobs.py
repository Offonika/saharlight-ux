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

    sig = inspect.signature(job_queue.run_once)
    supports_job_kwargs = "job_kwargs" in sig.parameters
    supports_name = "name" in sig.parameters

    call_kwargs: dict[str, Any] = {"when": when, "data": data}
    jk: dict[str, object] = dict(job_kwargs or {})

    if name is not None:
        if supports_job_kwargs:
            if "name" in jk or not supports_name:
                jk.setdefault("id", name)
                jk.setdefault("name", name)
            else:
                call_kwargs["name"] = name
                jk.setdefault("id", name)
        elif supports_name:
            call_kwargs["name"] = name

    if jk and supports_job_kwargs:
        call_kwargs["job_kwargs"] = jk

    run_once = cast(Any, job_queue.run_once)
    try:
        result = run_once(callback, timezone=tz, **call_kwargs)
    except TypeError:
        result = run_once(callback, **call_kwargs)
    return cast(Job[CustomContext], result)


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

    sig = inspect.signature(job_queue.run_daily)
    supports_job_kwargs = "job_kwargs" in sig.parameters
    supports_name = "name" in sig.parameters
    supports_days = "days" in sig.parameters

    call_kwargs: dict[str, Any] = {"time": time, "data": data}
    jk: dict[str, object] = dict(job_kwargs or {})

    if days is not None and supports_days:
        call_kwargs["days"] = tuple(days)

    if name is not None:
        if supports_job_kwargs:
            if "name" in jk or not supports_name:
                jk.setdefault("id", name)
                jk.setdefault("name", name)
            else:
                call_kwargs["name"] = name
                jk.setdefault("id", name)
        elif supports_name:
            call_kwargs["name"] = name

    if jk and supports_job_kwargs:
        call_kwargs["job_kwargs"] = jk

    run_daily = cast(Any, job_queue.run_daily)
    try:
        result = run_daily(callback, timezone=tz, **call_kwargs)
    except TypeError:
        result = run_daily(callback, **call_kwargs)
    return cast(Job[CustomContext], result)


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
