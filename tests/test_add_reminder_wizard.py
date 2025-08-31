from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, cast

import pytest
from datetime import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram import Update
from telegram.ext import ContextTypes

import services.api.app.diabetes.handlers.reminder_handlers as handlers
from services.api.app.diabetes.services.repository import commit
from services.api.app.diabetes.services.db import Base, Reminder, User
from services.api.app.reminder_events import set_job_queue
from services.api.app.reminders.common import DefaultJobQueue


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


class DummyJobQueue:
    def __init__(self) -> None:
        self.jobs: list[Any] = []

    def run_daily(
        self,
        callback: Callable[..., Any],
        time: Any,
        data: dict[str, Any] | None = None,
        name: str | None = None,
    ) -> None:
        pass

    def run_repeating(
        self,
        callback: Callable[..., Any],
        interval: Any,
        data: dict[str, Any] | None = None,
        name: str | None = None,
    ) -> None:
        pass

    def get_jobs_by_name(self, name: str) -> list[Any]:
        return []


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
    job_queue = DummyJobQueue()
    set_job_queue(cast(DefaultJobQueue, job_queue))
    context = cast(ContextTypes.DEFAULT_TYPE, CallbackContextStub(job_queue=job_queue))
    await handlers.reminder_webapp_save(update, context)
    set_job_queue(None)

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
    job_queue = DummyJobQueue()
    set_job_queue(cast(DefaultJobQueue, job_queue))
    context = cast(ContextTypes.DEFAULT_TYPE, CallbackContextStub(job_queue=job_queue))
    await handlers.reminder_webapp_save(update, context)
    set_job_queue(None)

    with TestSession() as session:
        rem = session.query(Reminder).first()
        assert rem and rem.interval_hours == 2
