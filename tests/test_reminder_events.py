from __future__ import annotations

import pytest
from typing import Any, cast

from services.api.app import reminder_events
from services.api.app.diabetes.services.db import Reminder


@pytest.mark.asyncio
async def test_notify_without_job_queue_raises() -> None:
    reminder_events.register_job_queue(None)
    with pytest.raises(RuntimeError):
        await reminder_events.notify_reminder_saved(1)


@pytest.mark.asyncio
async def test_notify_with_job_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummySession:
        def __enter__(self) -> DummySession:  # pragma: no cover - simple stub
            return self

        def __exit__(self, *exc: object) -> None:  # pragma: no cover - simple stub
            return None

        def get(self, *args: object, **kwargs: object) -> None:  # pragma: no cover
            return None

    monkeypatch.setattr(reminder_events, "SessionLocal", lambda: DummySession())
    reminder_events.register_job_queue(cast(Any, object()))
    await reminder_events.notify_reminder_saved(1)
    reminder_events.register_job_queue(None)


@pytest.mark.asyncio
async def test_notify_disabled_removes_job(monkeypatch: pytest.MonkeyPatch) -> None:
    rem = Reminder(id=1, telegram_id=1, type="sugar", is_enabled=False)

    class DummySession:
        def __enter__(self) -> DummySession:  # pragma: no cover - simple stub
            return self

        def __exit__(self, *exc: object) -> None:  # pragma: no cover - simple stub
            return None

        def get(self, model: object, _id: object) -> Reminder | None:
            return rem if model is Reminder else None

    class DummyJob:
        def __init__(self, queue: DummyJobQueue, name: str) -> None:
            self.queue = queue
            self.name = name

        def schedule_removal(self) -> None:
            self.queue.jobs.remove(self)

    class DummyJobQueue:
        def __init__(self) -> None:
            self.jobs: list[DummyJob] = []

        def get_jobs_by_name(self, name: str) -> list[DummyJob]:
            return [job for job in self.jobs if job.name.startswith(name)]

    jq = DummyJobQueue()
    jq.jobs.append(DummyJob(jq, "reminder_1"))

    monkeypatch.setattr(reminder_events, "SessionLocal", lambda: DummySession())
    reminder_events.register_job_queue(cast(Any, jq))
    await reminder_events.notify_reminder_saved(1)
    assert jq.get_jobs_by_name("reminder_1") == []
    reminder_events.register_job_queue(None)


@pytest.mark.asyncio
async def test_notify_after_event_removes_job(monkeypatch: pytest.MonkeyPatch) -> None:
    rem = Reminder(
        id=1,
        telegram_id=1,
        type="sugar",
        is_enabled=True,
        kind="after_event",
    )

    class DummySession:
        def __enter__(self) -> DummySession:  # pragma: no cover - simple stub
            return self

        def __exit__(self, *exc: object) -> None:  # pragma: no cover - simple stub
            return None

        def get(self, model: object, _id: object) -> Reminder | None:
            return rem if model is Reminder else None

    class DummyJob:
        def __init__(self, queue: DummyJobQueue, name: str) -> None:
            self.queue = queue
            self.name = name

        def schedule_removal(self) -> None:
            self.queue.jobs.remove(self)

    class DummyJobQueue:
        def __init__(self) -> None:
            self.jobs: list[DummyJob] = []

        def get_jobs_by_name(self, name: str) -> list[DummyJob]:
            return [job for job in self.jobs if job.name.startswith(name)]

    jq = DummyJobQueue()
    jq.jobs.append(DummyJob(jq, "reminder_1"))

    monkeypatch.setattr(reminder_events, "SessionLocal", lambda: DummySession())
    reminder_events.register_job_queue(cast(Any, jq))
    await reminder_events.notify_reminder_saved(1)
    assert jq.get_jobs_by_name("reminder_1") == []
    reminder_events.register_job_queue(None)
