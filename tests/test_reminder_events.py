from __future__ import annotations

import pytest
from typing import Any, cast

from services.api.app import reminder_events


def test_notify_without_job_queue_raises() -> None:
    reminder_events.register_job_queue(None)
    with pytest.raises(RuntimeError):
        reminder_events.notify_reminder_saved(1)


def test_notify_with_job_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummySession:
        def __enter__(self) -> DummySession:  # pragma: no cover - simple stub
            return self

        def __exit__(self, *exc: object) -> None:  # pragma: no cover - simple stub
            return None

        def get(self, *args: object, **kwargs: object) -> None:  # pragma: no cover
            return None

    monkeypatch.setattr(reminder_events, "SessionLocal", lambda: DummySession())
    reminder_events.register_job_queue(cast(Any, object()))
    reminder_events.notify_reminder_saved(1)
    reminder_events.register_job_queue(None)
