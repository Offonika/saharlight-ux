from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Any

from telegram.ext import ContextTypes, Job, JobQueue
from typing import TypeAlias

CustomContext: TypeAlias = ContextTypes.DEFAULT_TYPE
DefaultJobQueue: TypeAlias = JobQueue[ContextTypes.DEFAULT_TYPE]

JobCallback = Callable[[CustomContext], Awaitable[object] | object]


def schedule_once(
    job_queue: DefaultJobQueue,
    callback: JobCallback,
    *,
    when: datetime | timedelta | float,
    data: dict[str, object] | None = None,
    name: str | None = None,
    timezone: datetime.tzinfo | None = None,
) -> Job[CustomContext]:
    """Schedule ``callback`` to run once at ``when``.

    If ``job_queue.run_once`` supports a ``timezone`` argument, the job queue's
    timezone is forwarded automatically.  ``timezone`` can be provided
    explicitly; otherwise the timezone is derived from the job queue's
    application or scheduler.
    """
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
    if "timezone" in inspect.signature(job_queue.run_once).parameters:
        params["timezone"] = tz
    return job_queue.run_once(callback, **params)
