"""Job queue helpers and diagnostics.

This module provides utilities for scheduling jobs and :func:`dbg_jobs_dump`,
which exposes job IDs and names for debug purposes.
"""

from __future__ import annotations

import inspect
import logging
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


logger = logging.getLogger(__name__)

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


def _safe_remove(job: object) -> bool:
    """Remove ``job`` using best-effort strategies.

    The function sequentially tries ``job.remove()``,
    ``scheduler.remove_job(job_id=job.id)`` and ``job.schedule_removal()``.
    It returns ``True`` as soon as any of the attempts succeeds.
    """
    remover = cast(Callable[[], None] | None, getattr(job, "remove", None))
    if remover is not None:
        try:
            remover()
            return True
        except Exception:  # pragma: no cover - defensive
            pass

    queue = getattr(job, "queue", None)
    scheduler = getattr(queue, "scheduler", None)
    remove_job = cast(
        Callable[..., None] | None, getattr(scheduler, "remove_job", None)
    )
    job_id = getattr(job, "id", None)
    if remove_job is not None and job_id is not None:
        try:
            remove_job(job_id=job_id)
            return True
        except TypeError:  # pragma: no cover - APScheduler compatibility
            try:
                remove_job(job_id)
                return True
            except Exception:  # pragma: no cover - defensive
                pass
        except Exception:  # pragma: no cover - defensive
            pass

    schedule_removal = cast(
        Callable[[], None] | None, getattr(job, "schedule_removal", None)
    )
    if schedule_removal is not None:
        try:
            schedule_removal()
            return True
        except Exception:  # pragma: no cover - defensive
            pass
    return False


def _remove_jobs(job_queue: DefaultJobQueue, base_name: str) -> int:
    """Remove jobs matching ``base_name`` and related suffixes.

    Hard removal is required as APScheduler may keep stale jobs even when
    the job queue loses track of them. Leftover jobs could fire after
    restart, so we aggressively remove them. Returns the number of jobs
    removed.
    """
    names = {base_name, f"{base_name}_after", f"{base_name}_snooze"}
    removed = 0

    scheduler = getattr(job_queue, "scheduler", None)
    remove_job_direct = cast(
        Callable[..., None] | None, getattr(scheduler, "remove_job", None)
    )
    get_job_direct = cast(
        Callable[[str], object | None] | None, getattr(scheduler, "get_job", None)
    )
    jobs_attr = getattr(job_queue, "jobs", None)

    if remove_job_direct is not None:
        for name in names:
            existed = (
                get_job_direct is not None and get_job_direct(name) is not None
            )
            try:
                remove_job_direct(job_id=name)
            except TypeError:  # pragma: no cover - APScheduler compatibility
                try:
                    remove_job_direct(name)
                except Exception:  # pragma: no cover - defensive
                    pass
            except Exception:  # pragma: no cover - defensive
                pass
            if existed:
                removed += 1

    jobs_to_remove: set[object] = set()
    for name in names:
        jobs_to_remove.update(job_queue.get_jobs_by_name(name))
    for q_job in jobs_to_remove:
        if _safe_remove(q_job):
            removed += 1

    if jobs_attr is not None:
        jobs_iter = list(jobs_attr() if callable(jobs_attr) else jobs_attr)
        for any_job in jobs_iter:
            jname = getattr(any_job, "name", None)
            jid = getattr(any_job, "id", None)
            if any(
                (
                    isinstance(jname, str) and (jname == n or jname.startswith(n))
                )
                or (
                    isinstance(jid, str) and (jid == n or jid.startswith(n))
                )
                for n in names
            ):
                if _safe_remove(any_job):
                    removed += 1

    logger.debug("Removed %d jobs for base '%s'", removed, base_name)
    return removed


def dbg_jobs_dump(job_queue: DefaultJobQueue) -> list[tuple[str | None, str | None]]:
    """Collect ``(id, name)`` pairs for jobs in ``job_queue``."""

    jobs_attr = getattr(job_queue, "jobs", [])
    jobs_obj = jobs_attr() if callable(jobs_attr) else jobs_attr
    if isinstance(jobs_obj, dict):
        jobs_iter: Iterable[object] = (
            job for jobs in jobs_obj.values() for job in jobs
        )
    else:
        jobs_iter = cast(Iterable[object], jobs_obj)

    dump: list[tuple[str | None, str | None]] = []
    for job in jobs_iter:
        dump.append(
            (
                cast(str | None, getattr(job, "id", None)),
                cast(str | None, getattr(job, "name", None)),
            )
        )
    return dump
