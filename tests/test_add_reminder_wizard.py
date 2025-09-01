from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, cast

import pytest
from datetime import time, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock
from telegram import Update
from telegram.ext import ContextTypes

import services.api.app.diabetes.handlers.reminder_handlers as handlers
from services.api.app.diabetes.services.repository import commit
from services.api.app.diabetes.services.db import Base, Reminder, User


@dataclass
class WebAppData:
    data: str


class DummyMessage:
    def __init__(self, data: str) -> None:
        self.web_app_data: WebAppData = WebAppData(data)
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


class DummyScheduler:
    def __init__(self) -> None:
        self.jobs: list[Any] = []

    def add_job(
        self,
        func: Callable[..., Any],
        *,
        trigger: str,
        id: str,
        name: str,
        replace_existing: bool,
        timezone: object,
        kwargs: dict[str, Any] | None = None,
        **params: object,
    ) -> None:
        if replace_existing:
            self.jobs = [j for j in self.jobs if j["name"] != name]
        self.jobs.append({"name": name, "kwargs": kwargs, "params": params})


class DummyJobQueue:
    def __init__(self) -> None:
        self.scheduler = DummyScheduler()

    def run_daily(
        self,
        callback: Callable[..., Any],
        time: time,
        data: dict[str, Any] | None = None,
        name: str | None = None,
        timezone: object | None = None,
        days: tuple[int, ...] | None = None,
        job_kwargs: dict[str, Any] | None = None,
    ) -> None:
        job_id = job_kwargs.get("id") if job_kwargs else name
        if job_kwargs and job_kwargs.get("replace_existing"):
            self.scheduler.jobs = [j for j in self.scheduler.jobs if j["name"] != job_id]
        self.scheduler.jobs.append({"name": job_id, "kwargs": {"context": data}, "params": {"hour": time.hour, "minute": time.minute, "days": days}})

    def run_repeating(
        self,
        callback: Callable[..., Any],
        interval: timedelta,
        data: dict[str, Any] | None = None,
        name: str | None = None,
        first: object | None = None,
        job_kwargs: dict[str, Any] | None = None,
    ) -> None:
        job_id = job_kwargs.get("id") if job_kwargs else name
        if job_kwargs and job_kwargs.get("replace_existing"):
            self.scheduler.jobs = [j for j in self.scheduler.jobs if j["name"] != job_id]
        self.scheduler.jobs.append({"name": job_id, "kwargs": {"context": data}, "params": {"interval": interval}})

    def get_jobs_by_name(self, name: str) -> list[Any]:
        return [j for j in self.scheduler.jobs if j["name"] == name]


@dataclass
class DummyUser:
    id: int


@dataclass
class UpdateStub:
    effective_message: DummyMessage
    effective_user: DummyUser


@dataclass
class CallbackContextStub:
    job_queue: DummyJobQueue


@pytest.mark.asyncio
async def test_webapp_save_creates_reminder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    msg = DummyMessage(json.dumps({"type": "sugar", "value": "08:00"}))
    update = cast(Update, UpdateStub(effective_message=msg, effective_user=DummyUser(id=1)))
    context = cast(ContextTypes.DEFAULT_TYPE, CallbackContextStub(job_queue=DummyJobQueue()))
    monkeypatch.setattr(
        handlers.reminder_events,
        "notify_reminder_saved",
        AsyncMock(),
    )
    await handlers.reminder_webapp_save(update, context)

    with TestSession() as session:
        rem = session.query(Reminder).first()
        assert rem and rem.time == time(8, 0)


@pytest.mark.asyncio
async def test_webapp_save_creates_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    msg = DummyMessage(json.dumps({"type": "sugar", "value": "2h"}))
    update = cast(Update, UpdateStub(effective_message=msg, effective_user=DummyUser(id=1)))
    context = cast(ContextTypes.DEFAULT_TYPE, CallbackContextStub(job_queue=DummyJobQueue()))
    monkeypatch.setattr(
        handlers.reminder_events,
        "notify_reminder_saved",
        AsyncMock(),
    )
    await handlers.reminder_webapp_save(update, context)

    with TestSession() as session:
        rem = session.query(Reminder).first()
        assert rem and rem.interval_hours == 2
