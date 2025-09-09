from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, time as dt_time, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from services.api.app import reminder_events
from services.api.app.diabetes.handlers import reminder_handlers
from services.api.app.diabetes.services.db import Base, User
from services.api.app.routers import reminders as reminders_router
from services.api.app.services import reminders
from services.api.app.telegram_auth import check_token


class DummyJob:
    def __init__(self, name: str, run_time: dt_time | None = None) -> None:
        self.name = name
        self.run_time = run_time
        self.removed = False

    def schedule_removal(self) -> None:  # pragma: no cover - trivial
        self.removed = True


class DummyJobQueue:
    def __init__(self) -> None:
        self.jobs: list[DummyJob] = []

    def run_daily(
        self,
        callback: Any,
        time: dt_time,
        *,
        data: dict[str, Any] | None = None,
        name: str | None = None,
        job_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> DummyJob:
        if job_kwargs and job_kwargs.get("replace_existing"):
            self.jobs = [job for job in self.jobs if job.name != name]
        job = DummyJob(name or "", time)
        self.jobs.append(job)
        return job

    def run_repeating(
        self,
        callback: Any,
        interval: Any,
        *,
        data: dict[str, Any] | None = None,
        name: str | None = None,
        job_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> DummyJob:
        if job_kwargs and job_kwargs.get("replace_existing"):
            self.jobs = [job for job in self.jobs if job.name != name]
        job = DummyJob(name or "")
        self.jobs.append(job)
        return job

    def get_jobs_by_name(self, name: str) -> list[DummyJob]:
        return [job for job in self.jobs if job.name == name]


@pytest.fixture()
def session_factory() -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    try:
        yield TestSession
    finally:
        engine.dispose()


@pytest.fixture()
def client(
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[TestClient, None, None]:
    monkeypatch.setattr(reminders, "SessionLocal", session_factory)
    monkeypatch.setattr(reminder_events, "SessionLocal", session_factory)
    monkeypatch.setattr(reminder_handlers, "SessionLocal", session_factory)
    monkeypatch.setattr(
        reminders,
        "compute_next",
        lambda rem, tz: datetime(2023, 1, 1, tzinfo=timezone.utc),
    )
    app = FastAPI()
    app.include_router(reminders_router.router, prefix="/api")
    app.dependency_overrides[check_token] = lambda: {"id": 1}
    with TestClient(app) as test_client:
        yield test_client


def test_post_reminder_uses_job_queue(
    client: TestClient,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    fake_queue = DummyJobQueue()
    monkeypatch.setattr(reminder_events, "job_queue", fake_queue)
    spy = AsyncMock(wraps=reminder_events.notify_reminder_saved)
    monkeypatch.setattr(reminder_events, "notify_reminder_saved", spy)

    resp = client.post(
        "/api/reminders",
        json={"telegramId": 1, "type": "sugar", "time": "08:00", "isEnabled": True},
    )
    assert resp.status_code == 200
    rid = resp.json()["id"]
    spy.assert_awaited_once_with(rid)
    assert fake_queue.get_jobs_by_name(f"reminder_{rid}")

    reminder_events.job_queue = None


def test_edit_reminder_replaces_job(
    client: TestClient,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with session_factory() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    fake_queue = DummyJobQueue()
    monkeypatch.setattr(reminder_events, "job_queue", fake_queue)
    spy = AsyncMock(wraps=reminder_events.notify_reminder_saved)
    monkeypatch.setattr(reminder_events, "notify_reminder_saved", spy)

    resp = client.post(
        "/api/reminders",
        json={"telegramId": 1, "type": "sugar", "time": "08:00", "isEnabled": True},
    )
    assert resp.status_code == 200
    rid = resp.json()["id"]
    spy.assert_awaited_once_with(rid)
    assert [
        (j.run_time.hour, j.run_time.minute)
        for j in fake_queue.get_jobs_by_name(f"reminder_{rid}")
    ] == [(8, 0)]

    spy.reset_mock()

    resp = client.patch(
        "/api/reminders",
        json={
            "id": rid,
            "telegramId": 1,
            "type": "sugar",
            "time": "09:00",
            "isEnabled": True,
        },
    )
    assert resp.status_code == 200
    spy.assert_awaited_once_with(rid)
    jobs = fake_queue.get_jobs_by_name(f"reminder_{rid}")
    assert len(jobs) == 1
    assert (jobs[0].run_time.hour, jobs[0].run_time.minute) == (9, 0)

    reminder_events.job_queue = None

