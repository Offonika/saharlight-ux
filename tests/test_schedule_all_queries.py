from __future__ import annotations

from datetime import time
from typing import Callable, cast

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from zoneinfo import ZoneInfo

import services.api.app.diabetes.handlers.reminder_handlers as handlers
from services.api.app.diabetes.handlers.reminder_jobs import DefaultJobQueue
from services.api.app.diabetes.services.db import Base, Reminder, User as DbUser


class DummyJob:
    def __init__(self, name: str | None, data: dict[str, object] | None) -> None:
        self.name = name
        self.data = data
        self.removed = False

    def schedule_removal(self) -> None:  # pragma: no cover - test helper
        self.removed = True


class DummyJobQueue:
    def __init__(self) -> None:
        self._jobs: list[DummyJob] = []
        self.timezone = ZoneInfo("UTC")

    def run_daily(
        self,
        callback: Callable[..., object],
        time: object,
        data: dict[str, object] | None = None,
        name: str | None = None,
    ) -> DummyJob:
        job = DummyJob(name, data)
        self._jobs.append(job)
        return job

    def run_repeating(
        self,
        callback: Callable[..., object],
        interval: object,
        data: dict[str, object] | None = None,
        name: str | None = None,
    ) -> DummyJob:
        job = DummyJob(name, data)
        self._jobs.append(job)
        return job

    def run_once(
        self,
        callback: Callable[..., object],
        when: object,
        data: dict[str, object] | None = None,
        name: str | None = None,
    ) -> DummyJob:
        job = DummyJob(name, data)
        self._jobs.append(job)
        return job

    def get_jobs_by_name(self, name: str) -> list[DummyJob]:
        return [j for j in self._jobs if j.name == name]

    def jobs(self) -> list[DummyJob]:  # pragma: no cover - debug helper
        return list(self._jobs)


def _setup_session() -> tuple[sessionmaker[Session], Engine]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return TestSession, engine


def test_schedule_all_uses_constant_queries() -> None:
    TestSession, engine = _setup_session()
    handlers.SessionLocal = TestSession
    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t", timezone="UTC"))
        for _ in range(50):
            session.add(
                Reminder(
                    telegram_id=1,
                    type="sugar",
                    time=time(8, 0),
                    is_enabled=True,
                )
            )
        session.commit()
    queries: list[str] = []

    @event.listens_for(engine, "before_cursor_execute")
    def _count(
        _: object,
        __: object,
        statement: str,
        *___: object,
        **____: object,
    ) -> None:  # pragma: no cover - event hook
        if statement.lstrip().upper().startswith("SELECT"):
            queries.append("q")

    job_queue = cast(DefaultJobQueue, DummyJobQueue())
    handlers.schedule_all(job_queue)
    event.remove(engine, "before_cursor_execute", _count)
    assert len(queries) == 2
    assert len(job_queue.jobs()) == 50
