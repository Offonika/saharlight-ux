from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
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
        self.web_app_data = WebAppData(data)
        self.replies: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)


class DummyJobQueue:
    def __init__(self) -> None:
        self.jobs: list[Any] = []

    def run_daily(self, *args: Any, **kwargs: Any) -> None:
        pass

    def run_repeating(self, *args: Any, **kwargs: Any) -> None:
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
    context = cast(
        ContextTypes.DEFAULT_TYPE, CallbackContextStub(job_queue=DummyJobQueue())
    )
    await handlers.reminder_webapp_save(update, context)

    with TestSession() as session:
        rem = session.query(Reminder).first()
        assert rem and rem.time == "08:00"


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
    context = cast(
        ContextTypes.DEFAULT_TYPE, CallbackContextStub(job_queue=DummyJobQueue())
    )
    await handlers.reminder_webapp_save(update, context)

    with TestSession() as session:
        rem = session.query(Reminder).first()
        assert rem and rem.interval_hours == 2
