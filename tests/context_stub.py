from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from telegram.ext import Job, JobQueue


class AlertContext(Protocol):
    """Protocol for context objects used in alert handlers tests."""
    job: Job[Any] | None
    job_queue: JobQueue[Any] | None
    bot: Any | None


@dataclass
class ContextStub:
    job: Job[Any] | None = None
    job_queue: JobQueue[Any] | None = None
    bot: Any | None = None
