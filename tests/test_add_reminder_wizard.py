from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, cast

import pytest
from datetime import time
from zoneinfo import ZoneInfo

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
        time: Any,
        *,
        days: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6),
        data: dict[str, Any] | None = None,
        name: str | None = None,
        job_kwargs: dict[str, Any] | None = None,
    ) -> Any:
        params = {"hour": time.hour, "minute": time.minute}
        if days != (0, 1, 2, 3, 4, 5, 6):
            params["day_of_week"] = ",".join(str(d) for d in days)
        return self.scheduler.add_job(
            callback,
            trigger="cron",
            id=name or "",
            name=name or "",
            replace_existing=bool(job_kwargs and job_kwargs.get("replace_existing")),
            timezone=getattr(time, "tzinfo", None) or ZoneInfo("UTC"),
            kwargs={"context": data},
            **params,
        )

    def run_once(
        self,
        callback: Callable[..., Any],
        when: Any,
        *,
        data: dict[str, Any] | None = None,
        name: str | None = None,
        timezone: object | None = None,
        job_kwargs: dict[str, Any] | None = None,
    ) -> Any:
        params = {"when": when}
        return self.scheduler.add_job(
            callback,
            trigger="date",
            id=name or "",
            name=name or "",
            replace_existing=bool(job_kwargs and job_kwargs.get("replace_existing")),
            timezone=timezone or ZoneInfo("UTC"),
            kwargs={"context": data},
            **params,
        )

    def run_repeating(
        self,
        callback: Callable[..., Any],
        interval: Any,
        *,
        data: dict[str, Any] | None = None,
        name: str | None = None,
        job_kwargs: dict[str, Any] | None = None,
    ) -> Any:
        minutes = int(interval.total_seconds() / 60)
        return self.scheduler.add_job(
            callback,
            trigger="interval",
            id=name or "",
            name=name or "",
            replace_existing=bool(job_kwargs and job_kwargs.get("replace_existing")),
            timezone=ZoneInfo("UTC"),
            kwargs={"context": data},
            minutes=minutes,
        )

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
    update = cast(
        Update, UpdateStub(effective_message=msg, effective_user=DummyUser(id=1))
    )
    context = cast(
        ContextTypes.DEFAULT_TYPE, CallbackContextStub(job_queue=DummyJobQueue())
    )
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
    update = cast(
        Update, UpdateStub(effective_message=msg, effective_user=DummyUser(id=1))
    )
    context = cast(
        ContextTypes.DEFAULT_TYPE, CallbackContextStub(job_queue=DummyJobQueue())
    )
    monkeypatch.setattr(
        handlers.reminder_events,
        "notify_reminder_saved",
        AsyncMock(),
    )
    await handlers.reminder_webapp_save(update, context)

    with TestSession() as session:
        rem = session.query(Reminder).first()
        assert rem and rem.interval_hours == 2
