from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from telegram import Bot
from telegram.ext import Job, JobQueue


class AlertContext(Protocol):
    """Protocol for context objects used in alert handlers tests."""
    job: Job | None
    job_queue: JobQueue | None
    bot: Bot | None


@dataclass
class ContextStub:
    job: Job | None = None
    job_queue: JobQueue | None = None
    bot: Bot | None = None
