from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
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
) -> Job[CustomContext]:
    """Schedule ``callback`` to run once at ``when``.

    If ``job_queue.run_once`` supports a ``timezone`` argument, the job queue's
    timezone is forwarded automatically.
    """
    params: dict[str, Any] = {"when": when, "data": data, "name": name}
    if "timezone" in inspect.signature(job_queue.run_once).parameters:
        tz = getattr(job_queue, "timezone", None) or getattr(
            getattr(job_queue, "scheduler", None), "timezone", None
        )
        params["timezone"] = tz
        return job_queue.run_once(callback, **params)
    return job_queue.run_once(callback, **params)
