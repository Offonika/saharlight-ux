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


def _remove_jobs(job_queue: DefaultJobQueue, base_name: str) -> int:
    """Forcefully remove jobs matching ``base_name`` and its variants.

    ``JobQueue``/APScheduler sometimes keep dangling jobs even after normal
    removal. To avoid duplicate executions we aggressively try several
    strategies: direct ``job.remove()``, scheduler-level ``remove_job`` and
    finally ``schedule_removal``. All jobs named ``base_name`` along with
    ``*_after`` and ``*_snooze`` suffixes (and their prefixed variants) are
    targeted. Returns the number of jobs affected.
    """

    names = {base_name, f"{base_name}_after", f"{base_name}_snooze"}
    scheduler = getattr(job_queue, "scheduler", None)
    get_job = cast(Callable[[str], object] | None, getattr(scheduler, "get_job", None))
    remove_job_fn = cast(
        Callable[[str], None] | None, getattr(scheduler, "remove_job", None)
    )

    def _safe_remove(job: object) -> bool:
        """Best-effort single job removal."""

        remover = cast(Callable[[], None] | None, getattr(job, "remove", None))
        if remover is not None:
            try:
                remover()
                return True
            except Exception:  # pragma: no cover - defensive
                pass
        if scheduler is not None:
            job_id = getattr(job, "id", None)
            if job_id is not None:
                try:
                    scheduler.remove_job(job_id)
                    return True
                except Exception:  # pragma: no cover - defensive
                    pass
        schedule_removal = cast(
            Callable[[], None] | None, getattr(job, "schedule_removal", None)
        )
        if schedule_removal is not None:
            schedule_removal()
            return True
        return False

    removed = 0
    seen: set[int] = set()
    for name in names:
        name_removed = False
        for job in job_queue.get_jobs_by_name(name):
            if id(job) in seen:
                continue
            seen.add(id(job))
            if _safe_remove(job):
                removed += 1
                name_removed = True
        if scheduler is not None:
            sched_job = get_job(name) if get_job is not None else None
            if sched_job is not None and id(sched_job) not in seen:
                seen.add(id(sched_job))
                if _safe_remove(sched_job):
                    removed += 1
                    name_removed = True
            if not name_removed and remove_job_fn is not None:
                try:
                    remove_job_fn(name)
                    removed += 1
                except Exception:  # pragma: no cover - defensive
                    pass
    jobs_obj = getattr(job_queue, "jobs", [])
    jobs_iter = jobs_obj() if callable(jobs_obj) else jobs_obj
    for job in jobs_iter:
        if id(job) in seen:
            continue
        job_id = getattr(job, "id", "")
        job_name = getattr(job, "name", "")
        if any(
            (isinstance(job_id, str) and (job_id == n or job_id.startswith(n)))
            or (isinstance(job_name, str) and (job_name == n or job_name.startswith(n)))
            for n in names
        ):
            seen.add(id(job))
            if _safe_remove(job):
                removed += 1
    return removed
