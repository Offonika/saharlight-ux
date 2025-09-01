from __future__ import annotations

import logging
from datetime import time as dt_time
from typing import Callable
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app import reminder_events
from services.api.app.diabetes.handlers import reminder_handlers, reminder_jobs
from services.api.app.diabetes.services.db import Base, Reminder, User


class DummyJob:
    def __init__(self, scheduler: "DummyScheduler", *, id: str, name: str, run_time: dt_time) -> None:
        self._scheduler = scheduler
        self.id = id
        self.name = name
        self.run_time = run_time

    def remove(self) -> None:  # pragma: no cover - simple stub
        self._scheduler.jobs = [j for j in self._scheduler.jobs if j.id != self.id]

    def schedule_removal(self) -> None:  # pragma: no cover - simple stub
        self.remove()


class DummyScheduler:
    def __init__(self, tz: ZoneInfo) -> None:
        self.timezone = tz
        self.jobs: list[DummyJob] = []

    def add_job(
        self,
        func: Callable[..., object],
        *,
        trigger: str,
        id: str,
        name: str,
        replace_existing: bool,
        timezone: ZoneInfo,
        kwargs: dict[str, object],
        **params: object,
    ) -> DummyJob:
        if replace_existing:
            self.jobs = [j for j in self.jobs if j.id != id]
        run_time = dt_time(int(params["hour"]), int(params["minute"]))
        job = DummyJob(self, id=id, name=name, run_time=run_time)
        self.jobs.append(job)
        return job

    def remove_job(self, job_id: str) -> None:  # pragma: no cover - simple stub
        self.jobs = [j for j in self.jobs if j.id != job_id]


class DummyJobQueue:
    def __init__(self) -> None:
        tz = ZoneInfo("UTC")
        self.scheduler = DummyScheduler(tz)
        self.application = SimpleNamespace(timezone=tz, scheduler=self.scheduler)

    def run_daily(
        self,
        callback: Callable[..., object],
        time: dt_time,
        *,
        days: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6),
        data: dict[str, object] | None = None,
        name: str | None = None,
        timezone: ZoneInfo | None = None,
        job_kwargs: dict[str, object] | None = None,
    ) -> DummyJob:
        params: dict[str, object] = {"hour": time.hour, "minute": time.minute}
        if days != (0, 1, 2, 3, 4, 5, 6):
            params["day_of_week"] = ",".join(str(d) for d in days)
        return self.scheduler.add_job(
            callback,
            trigger="cron",
            id=name or "",
            name=name or "",
            replace_existing=bool(job_kwargs and job_kwargs.get("replace_existing")),
            timezone=timezone or ZoneInfo("UTC"),
            kwargs={"context": data},
            **params,
        )

    def run_repeating(
        self,
        callback: Callable[..., object],
        interval: object,
        *,
        data: dict[str, object] | None = None,
        name: str | None = None,
        timezone: ZoneInfo | None = None,
        job_kwargs: dict[str, object] | None = None,
    ) -> DummyJob:  # pragma: no cover - not used in test
        return self.scheduler.add_job(
            callback,
            trigger="interval",
            id=name or "",
            name=name or "",
            replace_existing=bool(job_kwargs and job_kwargs.get("replace_existing")),
            timezone=timezone or ZoneInfo("UTC"),
            kwargs={"context": data} if data is not None else {},
            hour=0,
            minute=0,
        )

    def get_jobs_by_name(self, name: str) -> list[DummyJob]:
        return [j for j in self.scheduler.jobs if j.name == name]


@pytest.fixture()
def session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.mark.asyncio
async def test_gc_replaces_outdated_job(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(reminder_events, "SessionLocal", session_factory)
    monkeypatch.setattr(reminder_handlers, "SessionLocal", session_factory)

    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t", timezone="UTC"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                time=dt_time(8, 0),
                is_enabled=True,
            )
        )
        session.commit()
        rem = session.get(Reminder, 1)
        user = session.get(User, 1)
    jq = DummyJobQueue()
    reminder_jobs.schedule_reminder(rem, jq, user)
    assert jq.get_jobs_by_name("reminder_1")[0].run_time == dt_time(8, 0)

    with session_factory() as session:
        rem = session.get(Reminder, 1)
        rem.time = dt_time(9, 0)
        session.commit()

    reminder_events.register_job_queue(jq)
    await reminder_events._reminders_gc(None)
    job = jq.get_jobs_by_name("reminder_1")[0]
    assert job.run_time == dt_time(9, 0)
    reminder_events.register_job_queue(None)


@pytest.mark.asyncio
async def test_gc_continues_after_schedule_failure(
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(reminder_events, "SessionLocal", session_factory)
    monkeypatch.setattr(reminder_handlers, "SessionLocal", session_factory)

    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t", timezone="UTC"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                time=dt_time(8, 0),
                is_enabled=True,
            )
        )
        session.add(
            Reminder(
                id=2,
                telegram_id=1,
                type="sugar",
                time=dt_time(9, 0),
                is_enabled=True,
            )
        )
        session.commit()

    jq = DummyJobQueue()
    reminder_events.register_job_queue(jq)
    calls: list[int] = []

    def schedule_mock(rem: Reminder, job_queue: DummyJobQueue, user: object) -> None:
        calls.append(rem.id)
        if rem.id == 1:
            raise RuntimeError("boom")
        job_queue.run_daily(lambda ctx: None, time=rem.time, name=f"reminder_{rem.id}")

    monkeypatch.setattr(reminder_events, "schedule_reminder", schedule_mock)

    with caplog.at_level(logging.ERROR):
        await reminder_events._reminders_gc(None)

    assert calls == [1, 2]
    assert jq.get_jobs_by_name("reminder_2")
    assert any(
        "Failed to schedule reminder 1" in record.message for record in caplog.records
    )
    reminder_events.register_job_queue(None)

