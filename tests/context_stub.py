from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class AlertContext(Protocol):
    """Protocol for context objects used in alert handlers tests."""
    job: Any | None
    job_queue: Any | None
    bot: Any | None


@dataclass
class ContextStub:
    job: Any | None = None
    job_queue: Any | None = None
    bot: Any | None = None
