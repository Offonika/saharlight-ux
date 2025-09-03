from __future__ import annotations

from datetime import time
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import services.api.app.diabetes.handlers.onboarding_handlers as onboarding
import services.api.app.diabetes.handlers.reminder_handlers as reminder_handlers
import services.api.app.services.onboarding_state as onboarding_state
from services.api.app.diabetes.services.db import Base, Reminder, User
from services.api.app.diabetes.services.repository import commit


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)


class DummyQuery:
    def __init__(self, message: DummyMessage, data: str) -> None:
        self.message = message
        self.data = data

    async def answer(self) -> None:  # pragma: no cover - interface only
        pass


class DummyJob:
    def __init__(self, name: str) -> None:
        self.name = name


class DummyJobQueue:
    def __init__(self) -> None:
        self._jobs: list[DummyJob] = []

    def run_daily(
        self,
        callback: Any,
        *,
        time: time,
        days: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6),
        data: dict[str, Any] | None = None,
        name: str | None = None,
        job_kwargs: dict[str, Any] | None = None,
        timezone: object | None = None,
    ) -> DummyJob:
        job = DummyJob(cast(str, name))
        self._jobs.append(job)
        return job

    def run_repeating(
        self,
        callback: Any,
        interval: Any,
        *,
        data: dict[str, Any] | None = None,
        name: str | None = None,
        job_kwargs: dict[str, Any] | None = None,
        timezone: object | None = None,
    ) -> DummyJob:
        job = DummyJob(cast(str, name))
        self._jobs.append(job)
        return job

    def get_jobs_by_name(self, name: str) -> list[DummyJob]:
        return [j for j in self._jobs if j.name == name]

    def jobs(self) -> list[DummyJob]:  # pragma: no cover - debugging helper
        return self._jobs


@pytest.mark.asyncio
async def test_onboarding_creates_reminder(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    onboarding.SessionLocal = TestSession
    reminder_handlers.SessionLocal = TestSession

    store: dict[int, dict[str, Any]] = {}
    steps: dict[int, int] = {}

    async def save_state(
        uid: int, step: int, data: dict[str, Any], variant: str | None = None
    ) -> None:
        steps[uid] = step
        store[uid] = dict(data)

    async def load_state(uid: int) -> Any | None:
        if uid not in steps:
            return None
        return SimpleNamespace(user_id=uid, step=steps[uid], data=store[uid], variant=None)

    async def complete_state(uid: int) -> None:  # pragma: no cover - no logic
        pass

    monkeypatch.setattr(onboarding_state, "save_state", save_state)
    monkeypatch.setattr(onboarding_state, "load_state", load_state)
    monkeypatch.setattr(onboarding_state, "complete_state", complete_state)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        commit(session)

    message = DummyMessage()
    query_sel = DummyQuery(message, f"{onboarding.CB_REMINDER_PREFIX}sugar_08")
    update_sel = cast(
        Update,
        SimpleNamespace(callback_query=query_sel, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    await onboarding.reminders_chosen(update_sel, context)

    jq = DummyJobQueue()
    context.job_queue = jq
    query_done = DummyQuery(message, onboarding.CB_DONE)
    update_done = cast(
        Update,
        SimpleNamespace(callback_query=query_done, effective_user=SimpleNamespace(id=1)),
    )
    state = await onboarding.reminders_chosen(update_done, context)
    assert state == ConversationHandler.END

    with TestSession() as session:
        rem = session.query(Reminder).one()
        assert rem.telegram_id == 1
        assert rem.type == "sugar"
        assert rem.time == time(8, 0)

    job_name = f"reminder_{rem.id}"
    assert jq.get_jobs_by_name(job_name)
    assert any("Сахар 08:00" in text for text in message.replies)

