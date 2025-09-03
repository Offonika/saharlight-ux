import pytest
from dataclasses import dataclass
from datetime import time
from types import SimpleNamespace
from typing import Any, cast

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

import services.api.app.diabetes.handlers.onboarding_handlers as onboarding
import services.api.app.diabetes.handlers.reminder_handlers as reminder_handlers
from services.api.app.diabetes.handlers.reminder_jobs import DefaultJobQueue
from services.api.app.diabetes.services.db import Base, Reminder, User, run_db
from services.api.app.diabetes.services.repository import commit
import services.api.app.services.onboarding_state as onboarding_state


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


class DummyQuery:
    def __init__(self, message: DummyMessage, data: str) -> None:
        self.message = message
        self.data = data

    async def answer(self) -> None:  # pragma: no cover - no logic
        pass


class DummyScheduler:
    def __init__(self) -> None:
        self.jobs: list[dict[str, Any]] = []

    def add_job(self, callback: Any, *, trigger: str, id: str, name: str, replace_existing: bool, timezone: Any, kwargs: dict[str, Any] | None = None, **params: Any) -> None:  # noqa: ANN001
        if replace_existing:
            self.jobs = [j for j in self.jobs if j["name"] != name]
        self.jobs.append({"name": name, "kwargs": kwargs, "params": params})


class DummyJobQueue(DefaultJobQueue):  # type: ignore[misc]
    def __init__(self) -> None:
        self.scheduler = DummyScheduler()

    def run_daily(self, callback: Any, *, time: Any, days: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6), data: dict[str, Any] | None = None, name: str | None = None, job_kwargs: dict[str, Any] | None = None) -> Any:  # noqa: ANN001
        params = {"hour": time.hour, "minute": time.minute}
        if days != (0, 1, 2, 3, 4, 5, 6):
            params["day_of_week"] = ",".join(str(d) for d in days)
        return self.scheduler.add_job(
            callback,
            trigger="cron",
            id=name or "",
            name=name or "",
            replace_existing=bool(job_kwargs and job_kwargs.get("replace_existing")),
            timezone=getattr(time, "tzinfo", None),
            kwargs={"context": data},
            **params,
        )

    def get_jobs_by_name(self, name: str) -> list[Any]:
        return [j for j in self.scheduler.jobs if j["name"] == name]


@dataclass
class DummyContext:
    user_data: dict[str, Any]
    job_queue: DummyJobQueue


@pytest.mark.asyncio
async def test_onboarding_creates_reminder(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    # patch DB session makers
    monkeypatch.setattr(onboarding, "SessionLocal", TestSession, raising=False)
    monkeypatch.setattr(reminder_handlers, "SessionLocal", TestSession, raising=False)

    # simple in-memory onboarding state store
    store: dict[int, dict[str, Any]] = {}
    steps: dict[int, int] = {}
    variants: dict[int, str | None] = {}

    async def save_state(user_id: int, step: int, data: dict[str, Any], variant: str | None = None) -> None:
        steps[user_id] = step
        store[user_id] = dict(data)
        variants[user_id] = variant

    class DummyState:
        def __init__(self, uid: int) -> None:
            self.user_id = uid
            self.step = steps[uid]
            self.data = store[uid]
            self.variant = variants[uid]
            self.completed_at = None

    async def load_state(user_id: int) -> DummyState | None:
        if user_id not in steps:
            return None
        return DummyState(user_id)

    async def complete_state(user_id: int) -> None:  # pragma: no cover - no logic
        pass

    monkeypatch.setattr(onboarding_state, "save_state", save_state)
    monkeypatch.setattr(onboarding_state, "load_state", load_state)
    monkeypatch.setattr(onboarding_state, "complete_state", complete_state)

    # ensure synchronous DB operations
    monkeypatch.setattr(reminder_handlers, "commit", commit, raising=False)
    monkeypatch.setattr(reminder_handlers, "run_db", None, raising=False)
    monkeypatch.setattr(onboarding, "run_db", run_db, raising=False)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    message = DummyMessage()
    user = SimpleNamespace(id=1)
    query = DummyQuery(message, f"{onboarding.CB_REMINDER_PREFIX}sugar_08")
    update = cast(Update, SimpleNamespace(callback_query=query, effective_user=user))
    context = cast(CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]], DummyContext(user_data={}, job_queue=DummyJobQueue()))

    state = await onboarding.reminders_chosen(update, context)
    assert state == onboarding.REMINDERS

    query_done = DummyQuery(message, onboarding.CB_DONE)
    update_done = cast(Update, SimpleNamespace(callback_query=query_done, effective_user=user))
    state = await onboarding.reminders_chosen(update_done, context)
    assert state == ConversationHandler.END

    with TestSession() as session:
        rem = session.query(Reminder).one()
        assert rem.telegram_id == 1
        assert rem.type == "sugar"
        assert rem.time == time(8, 0)

    jobs = context.job_queue.scheduler.jobs
    assert any(job["name"] == f"reminder_{rem.id}" for job in jobs)
    assert any("Сахар 08:00" in r for r in message.replies)


@pytest.mark.asyncio
async def test_preset_reminder_schedules_with_detached_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    monkeypatch.setattr(reminder_handlers, "SessionLocal", TestSession, raising=False)
    monkeypatch.setattr(reminder_handlers, "commit", commit, raising=False)
    monkeypatch.setattr(reminder_handlers, "run_db", None, raising=False)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="t"))
        session.commit()

    captured: dict[str, Any] = {}
    original_schedule = reminder_handlers.schedule_reminder

    def fake_schedule(
        rem: Reminder,
        job_queue: DefaultJobQueue | None,
        user: User | None,
    ) -> None:
        captured["user"] = user
        original_schedule(rem, job_queue, user)

    monkeypatch.setattr(reminder_handlers, "schedule_reminder", fake_schedule)

    job_queue = DummyJobQueue()
    rem = await reminder_handlers.create_reminder_from_preset(1, "sugar_08", job_queue)
    assert rem is not None
    assert captured["user"] is None
    assert any(job["name"] == f"reminder_{rem.id}" for job in job_queue.scheduler.jobs)
