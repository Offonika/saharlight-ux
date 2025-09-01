from __future__ import annotations

import json
import logging
from collections.abc import Generator
from datetime import datetime, time, timedelta, timezone, tzinfo
from types import SimpleNamespace
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Callable, cast

import pytest
import importlib
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    Update,
    User,
)
from telegram.ext import CallbackContext, Job, JobQueue

import services.api.app.diabetes.handlers.reminder_handlers as handlers
import services.api.app.diabetes.handlers.router as router
from services.api.app.diabetes.services.db import (
    Base,
    Reminder,
    ReminderLog,
    User as DbUser,
)
from services.api.app.diabetes.services.repository import commit
from services.api.app.diabetes.utils.helpers import parse_time_interval
from services.api.app.routers.reminders import router as reminders_router
from services.api.app.services import reminders
from services.api.app.telegram_auth import require_tg_user


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text: str | None = text
        self.texts: list[str] = []
        self.edited: tuple[str, dict[str, Any]] | None = None
        self.kwargs: list[dict[str, Any]] = []
        self.web_app_data: Any | None = None

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.kwargs.append(kwargs)

    async def edit_text(self, text: str, **kwargs: Any) -> None:
        self.edited = (text, kwargs)


class DummyCallbackQuery:
    def __init__(self, data: str, message: DummyMessage, id: str = "1") -> None:
        self.data = data
        self.message = message
        self.id = id
        self.answers: list[str | None] = []
        self.edited: tuple[str, dict[str, Any]] | None = None

    async def answer(self, text: str | None = None, **kwargs: Any) -> None:
        self.answers.append(text)

    async def edit_message_text(self, text: str, **kwargs: Any) -> None:
        self.edited = (text, kwargs)


class DummyBot:
    def __init__(self) -> None:
        self.messages: list[tuple[int | str, str, dict[str, Any]]] = []
        self.cb_answers: list[tuple[str, str | None]] = []

    async def send_message(self, chat_id: int | str, text: str, **kwargs: Any) -> None:
        self.messages.append((chat_id, text, kwargs))

    async def answer_callback_query(self, callback_query_id: str, text: str | None = None, **kwargs: Any) -> None:
        self.cb_answers.append((callback_query_id, text))


class DummyJob:
    def __init__(
        self,
        scheduler: "DummyScheduler",
        *,
        id: str,
        name: str,
        trigger: str,
        timezone: tzinfo,
        params: dict[str, Any],
    ) -> None:
        self._scheduler = scheduler
        self.id = id
        self.name = name
        self.trigger = trigger
        self.timezone = timezone
        self.params = params
        self.removed = False
        if "hour" in params and "minute" in params:
            self.time = time(int(params.get("hour", 0)), int(params.get("minute", 0)))
        else:
            self.time = None
        self.days = params.get("days")

    def remove(self) -> None:
        self.removed = True
        self._scheduler.jobs = [j for j in self._scheduler.jobs if j.id != self.id]

    def schedule_removal(self) -> None:
        self.remove()


class DummyScheduler:
    def __init__(self) -> None:
        self.jobs: list[DummyJob] = []

    def add_job(
        self,
        func: Callable[..., Any],
        *,
        trigger: str,
        id: str,
        name: str,
        replace_existing: bool,
        timezone: tzinfo,
        kwargs: dict[str, Any],
        **params: Any,
    ) -> DummyJob:  # noqa: D401 - simplified
        if replace_existing:
            self.jobs = [j for j in self.jobs if j.id != id]
        job = DummyJob(self, id=id, name=name, trigger=trigger, timezone=timezone, params=params)
        self.jobs.append(job)
        return job

    def remove_job(self, job_id: str) -> None:
        self.jobs = [j for j in self.jobs if j.id != job_id]


class DummyJobQueue:
    def __init__(self, timezone: tzinfo | None = None) -> None:
        self.scheduler = DummyScheduler()
        self.timezone = timezone

    def run_once(
        self,
        callback: Callable[..., Any],
        when: Any,
        data: dict[str, Any] | None = None,
        name: str | None = None,
        timezone: object | None = None,
        job_kwargs: dict[str, Any] | None = None,
    ) -> DummyJob:
        params: dict[str, Any] = {"when": when}
        job_id = job_kwargs["id"] if job_kwargs else name or ""  # type: ignore[assignment]
        job = DummyJob(
            self.scheduler,
            id=job_id,
            name=name or job_id,
            trigger="once",
            timezone=timezone or ZoneInfo("UTC"),
            params=params,
        )
        self.scheduler.jobs.append(job)
        return job

    def run_daily(
        self,
        callback: Callable[..., Any],
        time: time,
        data: dict[str, Any] | None = None,
        name: str | None = None,
        timezone: object | None = None,
        days: tuple[int, ...] | None = None,
        job_kwargs: dict[str, Any] | None = None,
    ) -> DummyJob:
        params: dict[str, Any] = {
            "hour": time.hour,
            "minute": time.minute,
            "days": days,
        }
        job_id = job_kwargs["id"] if job_kwargs else name or ""
        if job_kwargs and job_kwargs.get("replace_existing"):
            self.scheduler.jobs = [j for j in self.scheduler.jobs if j.id != job_id]
        job = DummyJob(
            self.scheduler,
            id=job_id,
            name=name or job_id,
            trigger="daily",
            timezone=timezone or ZoneInfo("UTC"),
            params=params,
        )
        self.scheduler.jobs.append(job)
        return job

    def run_repeating(
        self,
        callback: Callable[..., Any],
        interval: timedelta,
        data: dict[str, Any] | None = None,
        name: str | None = None,
        first: object | None = None,
        job_kwargs: dict[str, Any] | None = None,
    ) -> DummyJob:
        params: dict[str, Any] = {"interval": interval}
        job_id = job_kwargs["id"] if job_kwargs else name or ""
        if job_kwargs and job_kwargs.get("replace_existing"):
            self.scheduler.jobs = [j for j in self.scheduler.jobs if j.id != job_id]
        job = DummyJob(
            self.scheduler,
            id=job_id,
            name=name or job_id,
            trigger="interval",
            timezone=ZoneInfo("UTC"),
            params=params,
        )
        self.scheduler.jobs.append(job)
        return job

    def get_jobs_by_name(self, name: str) -> list[DummyJob]:
        return [j for j in self.scheduler.jobs if j.name == name]

    @property
    def jobs(self) -> list[DummyJob]:
        return self.scheduler.jobs


def make_user(user_id: int) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = user_id
    return user


def make_update(**kwargs: Any) -> Update:
    update = MagicMock(spec=Update)
    for key, value in kwargs.items():
        setattr(update, key, value)
    return cast(Update, update)


def make_context(
    **kwargs: Any,
) -> CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]]:
    context = MagicMock(spec=CallbackContext)
    for key, value in kwargs.items():
        setattr(context, key, value)
    return cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        context,
    )


def test_schedule_reminder_replaces_existing_job() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t", timezone="Europe/Moscow"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                time=time(8, 0),
                kind="at_time",
                is_enabled=True,
            )
        )
        session.commit()
    job_queue = cast(handlers.DefaultJobQueue, DummyJobQueue())
    with TestSession() as session:
        rem = session.get(Reminder, 1)
        user = session.get(DbUser, 1)
        assert rem is not None
        handlers.schedule_reminder(rem, job_queue, user)
        handlers.schedule_reminder(rem, job_queue, user)
    jobs: list[DummyJob] = list(job_queue.get_jobs_by_name("reminder_1"))
    assert len(jobs) == 1
    job = jobs[0]
    assert job.trigger == "daily"
    assert job.params["hour"] == 8
    assert job.params["minute"] == 0
    assert job.timezone == ZoneInfo("Europe/Moscow")


def test_schedule_reminder_requires_job_queue() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                time=time(8, 0),
                kind="at_time",
                is_enabled=True,
            )
        )
        session.commit()
        rem = session.get(Reminder, 1)
        user = session.get(DbUser, 1)
        assert rem is not None
        assert user is not None
    with pytest.raises(RuntimeError):
        handlers.schedule_reminder(rem, None, user)


def test_schedule_reminder_requires_telegram_id() -> None:
    job_queue = cast(handlers.DefaultJobQueue, DummyJobQueue())
    rem = Reminder(
        id=1,
        telegram_id=None,
        type="sugar",
        time=time(8, 0),
        is_enabled=True,
    )
    with pytest.raises(ValueError):
        handlers.schedule_reminder(rem, job_queue, None)


def test_schedule_reminder_without_user_defaults_to_utc() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    with TestSession() as session:
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                time=time(8, 0),
                kind="at_time",
                is_enabled=True,
            )
        )
        session.commit()
    job_queue = cast(handlers.DefaultJobQueue, DummyJobQueue())
    with TestSession() as session:
        rem = session.get(Reminder, 1)
        assert rem is not None
        handlers.schedule_reminder(rem, job_queue, None)
    jobs: list[DummyJob] = list(job_queue.get_jobs_by_name("reminder_1"))
    assert jobs
    job = jobs[0]
    assert job.timezone == ZoneInfo("UTC")
    assert job.params["hour"] == 8


def test_schedule_reminder_uses_user_timezone_when_queue_has_none() -> None:
    user = DbUser(telegram_id=1, thread_id="t", timezone="UTC")
    rem = Reminder(
        id=1,
        telegram_id=1,
        type="sugar",
        time=time(8, 0),
        kind="at_time",
        is_enabled=True,
        user=user,
    )
    job_queue = cast(handlers.DefaultJobQueue, DummyJobQueue())
    handlers.schedule_reminder(rem, job_queue, user)
    jobs: list[DummyJob] = list(job_queue.get_jobs_by_name("reminder_1"))
    assert jobs
    job = jobs[0]
    assert job.timezone == ZoneInfo("UTC")
    assert job.params["hour"] == 8
    assert job.params["minute"] == 0


def test_schedule_reminder_ignores_application_timezone() -> None:
    user = DbUser(telegram_id=1, thread_id="t", timezone="Europe/Moscow")
    rem = Reminder(
        id=1,
        telegram_id=1,
        type="sugar",
        time=time(8, 0),
        kind="at_time",
        is_enabled=True,
        user=user,
    )
    job_queue = cast(handlers.DefaultJobQueue, DummyJobQueue())
    job_queue.application = SimpleNamespace(timezone=ZoneInfo("UTC"))
    handlers.schedule_reminder(rem, job_queue, user)
    jobs: list[DummyJob] = list(job_queue.get_jobs_by_name("reminder_1"))
    assert jobs
    job = jobs[0]
    assert job.timezone == ZoneInfo("Europe/Moscow")
    assert job.params["hour"] == 8


def test_schedule_reminder_respects_days_mask() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t", timezone="Europe/Moscow"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                time=time(8, 0),
                kind="at_time",
                is_enabled=True,
                days_mask=(1 << 0) | (1 << 2),
            )
        )
        session.commit()
    job_queue = cast(handlers.DefaultJobQueue, DummyJobQueue())
    with TestSession() as session:
        rem = session.get(Reminder, 1)
        user = session.get(DbUser, 1)
        assert rem is not None
        assert user is not None
        handlers.schedule_reminder(rem, job_queue, user)
    job = job_queue.get_jobs_by_name("reminder_1")[0]
    assert job.params.get("days") == (0, 2)


def test_schedule_with_next_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2024, 1, 1, 10, 0)

    class DummyDatetime(datetime):
        @classmethod
        def now(cls, tz: tzinfo | None = None) -> "DummyDatetime":
            result = now
            if tz is not None:
                result = result.replace(tzinfo=tz)
            return cast("DummyDatetime", result)

    monkeypatch.setattr(handlers, "datetime", DummyDatetime)
    user = DbUser(telegram_id=1, thread_id="t", timezone="Europe/Moscow")
    rem = Reminder(telegram_id=1, type="sugar", interval_hours=2, is_enabled=True, user=user)
    icon, schedule = handlers._schedule_with_next(rem)
    assert icon == "⏱"
    assert schedule == "каждые 2 ч (next 12:00)"


def test_schedule_with_next_without_user(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime(2024, 1, 1, 10, 0)

    class DummyDatetime(datetime):
        @classmethod
        def now(cls, tz: tzinfo | None = None) -> "DummyDatetime":
            result = now
            if tz is not None:
                result = result.replace(tzinfo=tz)
            return cast("DummyDatetime", result)

    monkeypatch.setattr(handlers, "datetime", DummyDatetime)
    rem = Reminder(
        telegram_id=1,
        type="sugar",
        time=time(12, 0),
        is_enabled=True,
    )
    icon, schedule = handlers._schedule_with_next(rem)
    assert icon == "⏰"
    assert schedule == "12:00 (next 12:00)"


def test_interval_minutes_scheduling_and_rendering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t", timezone="UTC"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                interval_minutes=30,
                kind="every",
                is_enabled=True,
            )
        )
        session.commit()

    job_queue = cast(handlers.DefaultJobQueue, DummyJobQueue())
    job_queue.application = SimpleNamespace(timezone=ZoneInfo("UTC"))
    with TestSession() as session:
        rem = session.get(Reminder, 1)
        user = session.get(DbUser, 1)
        assert rem is not None
        with patch.object(job_queue, "run_repeating", wraps=job_queue.run_repeating) as mock_rep:
            handlers.schedule_reminder(rem, job_queue, user)
            mock_rep.assert_called_once()
            assert mock_rep.call_args.kwargs["interval"] == timedelta(minutes=30)
        text, _ = handlers._render_reminders(session, 1)
    assert "⏱ Интервал" in text
    assert "каждые 30 мин" in text


def test_schedule_with_next_invalid_timezone_logs_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    user = DbUser(telegram_id=1, thread_id="t", timezone="Invalid/Zone")
    rem = Reminder(
        telegram_id=1,
        type="sugar",
        time=time(8, 0),
        kind="at_time",
        is_enabled=True,
        user=user,
    )
    with caplog.at_level(logging.WARNING):
        icon, schedule = handlers._schedule_with_next(rem)
    assert icon == "⏰"
    assert any("Invalid timezone" in r.message for r in caplog.records)


def test_schedule_reminder_invalid_timezone_raises() -> None:
    user = DbUser(telegram_id=1, thread_id="t", timezone="Bad/Zone")
    rem = Reminder(id=1, telegram_id=1, type="sugar", time=time(8, 0), is_enabled=True, user=user)
    job_queue = cast(handlers.DefaultJobQueue, DummyJobQueue())
    with pytest.raises(ZoneInfoNotFoundError):
        handlers.schedule_reminder(rem, job_queue, user)


def test_render_reminders_formatting(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setenv("PUBLIC_ORIGIN", "https://example.org")
    monkeypatch.setenv("UI_BASE_URL", "/ui")
    import services.api.app.config as config

    importlib.reload(config)
    importlib.reload(handlers)
    handlers.SessionLocal = TestSession
    monkeypatch.setattr(handlers, "_limit_for", lambda u: 1)
    # Make _describe deterministic and include status icon to test strikethrough
    monkeypatch.setattr(
        handlers,
        "_describe",
        lambda r, u=None: f"{'🔔' if r.is_enabled else '🔕'}title{r.id}",
    )

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add_all(
            [
                Reminder(
                    id=1,
                    telegram_id=1,
                    type="sugar",
                    time=time(8, 0),
                    kind="at_time",
                    is_enabled=True,
                ),
                Reminder(
                    id=2,
                    telegram_id=1,
                    type="sugar",
                    interval_hours=3,
                    kind="every",
                    is_enabled=False,
                ),
                Reminder(
                    id=3,
                    telegram_id=1,
                    type="after_meal",
                    minutes_after=15,
                    kind="after_event",
                    is_enabled=True,
                ),
            ]
        )
        session.commit()
    with TestSession() as session:
        text, markup = handlers._render_reminders(session, 1)
    assert markup is not None
    header, *rest = text.splitlines()
    assert header == "Ваши напоминания  (2 / 1 🔔) ⚠️"
    assert "⏰ По времени" in text
    assert "⏱ Интервал" in text
    assert "📸 Триггер-фото" in text
    assert "2. <s>🔕title2</s>" in text
    assert markup.inline_keyboard
    assert len(markup.inline_keyboard) == 4
    for rem_id, row in zip([1, 2, 3], markup.inline_keyboard[:-1]):
        edit_btn = row[0]
        assert edit_btn.text == "✏️"
        assert edit_btn.web_app is not None
        assert edit_btn.web_app.url == config.build_ui_url(f"/reminders?id={rem_id}")
    add_btn = markup.inline_keyboard[-1][0]
    assert add_btn.text == "➕ Добавить"
    assert add_btn.web_app is not None
    assert add_btn.web_app.url == config.build_ui_url("/reminders/new")


def test_render_reminders_no_webapp(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setenv("PUBLIC_ORIGIN", "")
    monkeypatch.setenv("UI_BASE_URL", "")
    import services.api.app.config as config

    importlib.reload(config)
    importlib.reload(handlers)
    handlers.SessionLocal = TestSession
    settings = config.get_settings()
    monkeypatch.setattr(settings, "public_origin", "")
    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                time=time(8, 0),
                kind="at_time",
                is_enabled=True,
            )
        )
        session.commit()
    with TestSession() as session:
        text, markup = handlers._render_reminders(session, 1)
    assert markup is not None
    assert "Нажмите кнопку" not in text
    assert len(markup.inline_keyboard) == 2
    first_row = markup.inline_keyboard[0]
    texts = [btn.text for btn in first_row]
    assert texts == ["✏️", "🗑️", "🔔"]
    assert first_row[0].callback_data == "rem_edit:1"
    assert all(btn.web_app is None for btn in first_row)
    add_row = markup.inline_keyboard[1]
    assert [btn.text for btn in add_row] == ["➕ Добавить"]
    assert add_row[0].callback_data == "rem_add"


def test_render_reminders_no_entries_no_webapp(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setenv("PUBLIC_ORIGIN", "")
    monkeypatch.setenv("UI_BASE_URL", "")
    import services.api.app.config as config

    importlib.reload(config)
    importlib.reload(handlers)
    handlers.SessionLocal = TestSession
    settings = config.get_settings()
    monkeypatch.setattr(settings, "public_origin", "")
    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.commit()
    with TestSession() as session:
        text, markup = handlers._render_reminders(session, 1)
    assert "У вас нет напоминаний" in text
    assert "Нажмите кнопку" in text
    assert markup is not None
    assert len(markup.inline_keyboard) == 1
    add_row = markup.inline_keyboard[0]
    assert [btn.text for btn in add_row] == ["➕ Добавить"]
    assert add_row[0].callback_data == "rem_add"


def test_render_reminders_no_entries_webapp(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setenv("PUBLIC_ORIGIN", "https://example.org")
    monkeypatch.setenv("UI_BASE_URL", "/ui")
    import services.api.app.config as config

    importlib.reload(config)
    importlib.reload(handlers)
    handlers.SessionLocal = TestSession
    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.commit()
    with TestSession() as session:
        text, markup = handlers._render_reminders(session, 1)
    assert "У вас нет напоминаний" in text
    assert "Нажмите кнопку" in text
    assert markup is not None
    assert len(markup.inline_keyboard) == 1
    add_row = markup.inline_keyboard[0]
    assert [btn.text for btn in add_row] == ["➕ Добавить"]
    add_btn = add_row[0]
    assert add_btn.web_app is not None
    assert add_btn.web_app.url == config.build_ui_url("/reminders/new")


def test_render_reminders_runtime_public_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    import services.api.app.config as config

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                time=time(8, 0),
                kind="at_time",
                is_enabled=True,
            )
        )
        session.commit()

    settings = config.get_settings()
    monkeypatch.setattr(settings, "public_origin", "")
    with TestSession() as session:
        _, markup = handlers._render_reminders(session, 1)
    assert markup is not None
    first_row = markup.inline_keyboard[0]
    assert first_row[0].callback_data == "rem_edit:1"
    add_row = markup.inline_keyboard[1]
    assert add_row[0].callback_data == "rem_add"

    monkeypatch.setattr(settings, "public_origin", "https://example.org")
    with TestSession() as session:
        _, markup = handlers._render_reminders(session, 1)
    assert markup is not None
    first_row = markup.inline_keyboard[0]
    edit_btn = first_row[0]
    assert edit_btn.web_app is not None
    assert edit_btn.web_app.url == config.build_ui_url("/reminders?id=1")
    add_btn = markup.inline_keyboard[1][0]
    assert add_btn.web_app is not None
    assert add_btn.web_app.url == config.build_ui_url("/reminders/new")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "keyboard",
    [InlineKeyboardMarkup([[InlineKeyboardButton("ok", callback_data="1")]]), None],
)
async def test_reminders_list_renders_output(
    monkeypatch: pytest.MonkeyPatch, keyboard: InlineKeyboardMarkup | None
) -> None:
    monkeypatch.setattr(handlers, "run_db", None)

    session_obj = object()

    class DummySessionCtx:
        def __enter__(self) -> object:
            return session_obj

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            return None

    monkeypatch.setattr(handlers, "SessionLocal", lambda: DummySessionCtx())

    def fake_render(session: Session, user_id: int) -> tuple[str, InlineKeyboardMarkup | None]:
        assert session is session_obj
        assert user_id == 1
        return "rendered", keyboard

    monkeypatch.setattr(handlers, "_render_reminders", fake_render)

    captured: list[tuple[str, dict[str, Any]]] = []

    async def fake_reply_text(text: str, **kwargs: Any) -> None:
        captured.append((text, kwargs))

    message = MagicMock(spec=Message)
    message.reply_text = fake_reply_text
    update = make_update(effective_user=make_user(1), message=message)
    context = make_context()

    await handlers.reminders_list(update, context)

    assert captured[-1][0] == "rendered"
    kwargs = captured[-1][1]
    assert kwargs.get("parse_mode") == "HTML"
    if keyboard is not None:
        assert kwargs.get("reply_markup") is keyboard
    else:
        assert "reply_markup" not in kwargs


@pytest.mark.asyncio
async def test_reminders_list_shows_menu_keyboard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(handlers, "run_db", None)

    session_obj = object()

    class DummySessionCtx:
        def __enter__(self) -> object:
            return session_obj

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            return None

    monkeypatch.setattr(handlers, "SessionLocal", lambda: DummySessionCtx())

    def fake_render(session: Session, user_id: int) -> tuple[str, InlineKeyboardMarkup | None]:
        return "rendered", None

    monkeypatch.setattr(handlers, "_render_reminders", fake_render)

    sentinel_markup = ReplyKeyboardMarkup([[]])
    monkeypatch.setattr(handlers, "menu_keyboard", lambda: sentinel_markup)

    captured: list[tuple[str, dict[str, Any]]] = []

    async def fake_reply_text(text: str, **kwargs: Any) -> None:
        captured.append((text, kwargs))

    message = MagicMock(spec=Message)
    message.reply_text = fake_reply_text
    update = make_update(effective_user=make_user(1), message=message)
    context = make_context()

    await handlers.reminders_list(update, context)

    assert len(captured) == 2
    first_text, first_kwargs = captured[0]
    assert first_text == "📋 Выберите действие:"
    assert first_kwargs.get("reply_markup") is sentinel_markup


@pytest.mark.asyncio
async def test_toggle_reminder_cb(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time=time(8, 0), is_enabled=True))
        session.commit()

    job_queue = cast(handlers.DefaultJobQueue, DummyJobQueue())
    monkeypatch.setattr(
        handlers.reminder_events,
        "notify_reminder_saved",
        AsyncMock(),
    )
    with TestSession() as session:
        rem = session.get(Reminder, 1)
        user = session.get(DbUser, 1)
        assert rem is not None
        handlers.schedule_reminder(rem, job_queue, user)

    query = DummyCallbackQuery("rem_toggle:1", DummyMessage())
    update = make_update(callback_query=query, effective_user=make_user(1))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        make_context(job_queue=job_queue, user_data={"pending_entry": {}}),
    )
    await handlers.reminder_action_cb(update, context)
    await router.callback_router(update, context)

    with TestSession() as session:
        rem_db = session.get(Reminder, 1)
        assert rem_db is not None
        assert not rem_db.is_enabled
    jobs: list[DummyJob] = list(job_queue.get_jobs_by_name("reminder_1"))
    assert not jobs
    assert query.answers
    answer = query.answers[0]
    assert answer == "Готово ✅"
    assert context.user_data is not None
    user_data = context.user_data
    assert "pending_entry" in user_data


@pytest.mark.asyncio
async def test_delete_reminder_cb(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                time=time(8, 0),
                kind="at_time",
            )
        )
        session.commit()

    job_queue = cast(handlers.DefaultJobQueue, DummyJobQueue())
    with TestSession() as session:
        rem = session.get(Reminder, 1)
        user = session.get(DbUser, 1)
        assert rem is not None
        handlers.schedule_reminder(rem, job_queue, user)
    notify_mock = AsyncMock()
    monkeypatch.setattr(handlers.reminder_events, "notify_reminder_saved", notify_mock)

    query = DummyCallbackQuery("rem_del:1", DummyMessage())
    update = make_update(callback_query=query, effective_user=make_user(1))
    context = make_context(job_queue=job_queue, user_data={})
    await handlers.reminder_action_cb(update, context)
    notify_mock.assert_not_awaited()

    with TestSession() as session:
        assert session.query(Reminder).count() == 0
    jobs: list[DummyJob] = list(job_queue.get_jobs_by_name("reminder_1"))
    assert not jobs
    assert query.answers
    answer = query.answers[-1]
    assert answer == "Готово ✅"


@pytest.mark.asyncio
async def test_toggle_reminder_without_job_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time=time(8, 0), is_enabled=False))
        session.commit()

    schedule_mock = MagicMock()
    monkeypatch.setattr(handlers, "schedule_reminder", schedule_mock)
    notify_mock2 = AsyncMock()
    monkeypatch.setattr(
        handlers.reminder_events,
        "notify_reminder_saved",
        notify_mock2,
    )

    query = DummyCallbackQuery("rem_toggle:1", DummyMessage())
    update = make_update(callback_query=query, effective_user=make_user(1))
    context = make_context(job_queue=None, user_data={})
    await handlers.reminder_action_cb(update, context)

    with TestSession() as session:
        rem_db = session.get(Reminder, 1)
    assert rem_db is not None
    assert rem_db.is_enabled

    assert not schedule_mock.called
    notify_mock2.assert_awaited_once_with(1)


@pytest.mark.asyncio
async def test_toggle_reminder_missing_user(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time=time(8, 0), is_enabled=False))
        session.commit()

    reschedule_mock = MagicMock()
    monkeypatch.setattr(handlers, "_reschedule_job", reschedule_mock)
    notify_mock = AsyncMock()
    monkeypatch.setattr(handlers.reminder_events, "notify_reminder_saved", notify_mock)

    query = DummyCallbackQuery("rem_toggle:1", DummyMessage())
    update = make_update(callback_query=query, effective_user=make_user(1))
    job_queue = cast(handlers.DefaultJobQueue, DummyJobQueue())
    context = make_context(job_queue=job_queue, user_data={})
    with caplog.at_level(logging.WARNING):
        await handlers.reminder_action_cb(update, context)

    reschedule_mock.assert_not_called()
    assert "User 1 not found for rescheduling reminder 1" in caplog.text
    notify_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_edit_reminder(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="custom",
                time=time(8, 0),
                kind="at_time",
            )
        )
        session.commit()

    job_queue = cast(handlers.DefaultJobQueue, DummyJobQueue())
    with TestSession() as session:
        rem = session.get(Reminder, 1)
        user = session.get(DbUser, 1)
        assert rem is not None
        handlers.schedule_reminder(rem, job_queue, user)
    monkeypatch.setattr(
        handlers.reminder_events,
        "notify_reminder_saved",
        AsyncMock(),
    )

    msg = DummyMessage()
    web_app_data = MagicMock()
    web_app_data.data = json.dumps({"id": 1, "type": "custom", "value": "09:00"})
    msg.web_app_data = web_app_data
    update = make_update(effective_message=msg, effective_user=make_user(1))
    context = make_context(job_queue=job_queue)
    await handlers.reminder_webapp_save(update, context)

    with TestSession() as session:
        parsed = parse_time_interval("09:00")
        assert isinstance(parsed, time)
        rem_db = session.get(Reminder, 1)
        assert rem_db is not None
        assert rem_db.time == parsed
    jobs: list[DummyJob] = list(job_queue.get_jobs_by_name("reminder_1"))
    assert len(jobs) == 1
    job = jobs[0]
    assert job.time == time(9, 0)


@pytest.mark.asyncio
async def test_trigger_job_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                time=time(23, 0),
                kind="at_time",
            )
        )
        session.commit()

    job_queue = cast(handlers.DefaultJobQueue, DummyJobQueue())
    with TestSession() as session:
        rem_db = session.get(Reminder, 1)
        assert rem_db is not None
        rem = Reminder(
            id=rem_db.id,
            telegram_id=rem_db.telegram_id,
            type=rem_db.type,
            time=rem_db.time,
            kind=rem_db.kind,
        )
    with TestSession() as session:
        user = session.get(DbUser, 1)
    handlers.schedule_reminder(rem, job_queue, user)
    bot = DummyBot()
    job = MagicMock(spec=Job)
    job.data = {"reminder_id": 1, "chat_id": 1}
    context = make_context(bot=bot, job=job, job_queue=job_queue)
    await handlers.reminder_job(context)
    assert bot.messages
    _, text_msg, kwargs = bot.messages[0]
    assert kwargs is not None
    assert text_msg.startswith("🔔 Замерить сахар")
    reply_markup = kwargs.get("reply_markup")
    assert reply_markup is not None
    assert reply_markup.inline_keyboard

    keyboard = reply_markup.inline_keyboard[0]
    assert len(keyboard) >= 2
    assert keyboard[0].callback_data == "remind_snooze:1:10"
    assert keyboard[1].callback_data == "remind_cancel:1"

    with TestSession() as session:
        log = session.query(ReminderLog).first()
        assert log is not None
        assert log.action == "trigger"
        assert log.snooze_minutes is None


@pytest.mark.asyncio
async def test_snooze_callback_custom_delay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time=time(8, 0)))
        session.commit()

    query = DummyCallbackQuery("remind_snooze:1:15", DummyMessage())
    update = make_update(callback_query=query, effective_user=make_user(1))
    job_queue = MagicMock(spec=JobQueue)
    job_queue.run_once = MagicMock()
    context = make_context(job_queue=job_queue, bot=DummyBot())
    await handlers.reminder_callback(update, context)
    job_queue.run_once.assert_called_once()
    _, kwargs = job_queue.run_once.call_args
    assert kwargs["when"] == timedelta(minutes=15)
    assert kwargs["data"] == {"reminder_id": 1, "chat_id": 1}
    assert kwargs["name"] == "reminder_1"
    assert query.edited is not None
    edited_text, _ = query.edited
    assert edited_text == "⏰ Отложено на 15 минут"
    assert query.answers == [None]
    with TestSession() as session:
        log = session.query(ReminderLog).first()
        assert log is not None
        assert log.action == "remind_snooze"
        assert log.snooze_minutes == 15


@pytest.mark.asyncio
async def test_cancel_callback(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time=time(8, 0)))
        session.commit()

    query = DummyCallbackQuery("remind_cancel:1", DummyMessage())
    update = make_update(callback_query=query, effective_user=make_user(1))
    context = make_context(job_queue=DummyJobQueue(), bot=DummyBot())
    await handlers.reminder_callback(update, context)
    assert query.edited is not None
    edited_text, _ = query.edited
    assert edited_text == "❌ Напоминание отменено"
    assert query.answers == [None]
    with TestSession() as session:
        log = session.query(ReminderLog).first()
        assert log is not None
        assert log.action == "remind_cancel"
        assert log.snooze_minutes is None


@pytest.mark.asyncio
async def test_snooze_callback_default_delay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time=time(8, 0)))
        session.commit()

    query = DummyCallbackQuery("remind_snooze:1", DummyMessage())
    job_queue = DummyJobQueue()
    context = make_context(job_queue=job_queue, bot=DummyBot())
    update = make_update(callback_query=query, effective_user=make_user(1))
    await handlers.reminder_callback(update, context)

    assert query.edited is not None
    edited_text, _ = query.edited
    assert edited_text == "⏰ Отложено на 10 минут"
    assert query.answers == [None]
    assert job_queue.jobs
    with TestSession() as session:
        log = session.query(ReminderLog).first()
        assert log is not None
        assert log.action == "remind_snooze"
        assert log.snooze_minutes == 10


@pytest.mark.asyncio
async def test_snooze_callback_logs_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time=time(8, 0)))
        session.commit()

    query = DummyCallbackQuery("remind_snooze:1:15", DummyMessage())
    job_queue = MagicMock(spec=DummyJobQueue)
    context = make_context(job_queue=job_queue)
    update = make_update(callback_query=query, effective_user=make_user(1))
    await handlers.reminder_callback(update, context)

    job_queue.run_once.assert_called_once()
    _, kwargs = job_queue.run_once.call_args
    assert kwargs["when"] == timedelta(minutes=15)
    assert kwargs["data"] == {"reminder_id": 1, "chat_id": 1}
    assert kwargs["name"] == "reminder_1"
    assert query.edited is not None
    edited_text, _ = query.edited
    assert edited_text == "⏰ Отложено на 15 минут"
    assert query.answers == [None]
    with TestSession() as session:
        log = session.query(ReminderLog).first()
        assert log is not None
        assert log.action == "remind_snooze"


@pytest.mark.asyncio
async def test_snooze_callback_schedules_job_and_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time=time(8, 0)))
        session.commit()

    job_queue = cast(handlers.DefaultJobQueue, DummyJobQueue())
    run_once_mock = MagicMock(wraps=job_queue.run_once)
    job_queue.run_once = run_once_mock  # type: ignore[assignment]

    query = DummyCallbackQuery("remind_snooze:1", DummyMessage())
    update = make_update(callback_query=query, effective_user=make_user(1))
    context = make_context(job_queue=job_queue, bot=DummyBot())
    await handlers.reminder_callback(update, context)

    run_once_mock.assert_called_once()
    when = run_once_mock.call_args.kwargs["when"]
    assert when == timedelta(minutes=10)
    assert run_once_mock.call_args.kwargs["data"] == {
        "reminder_id": 1,
        "chat_id": 1,
    }
    assert run_once_mock.call_args.kwargs["name"] == "reminder_1"
    assert query.edited is not None
    edited_text, _ = query.edited
    assert edited_text == "⏰ Отложено на 10 минут"
    with TestSession() as session:
        log = session.query(ReminderLog).first()
        assert log is not None
        assert log.action == "remind_snooze"


@pytest.mark.asyncio
async def test_reminder_callback_foreign_rid(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    handlers.SessionLocal = TestSession
    handlers.commit = commit

    with TestSession() as session:
        session.add(DbUser(telegram_id=1, thread_id="t"))
        session.add(Reminder(id=1, telegram_id=1, type="sugar", time=time(8, 0)))
        session.commit()

    query = DummyCallbackQuery("remind_cancel:1", DummyMessage())
    update = make_update(callback_query=query, effective_user=make_user(2))
    context = make_context(job_queue=DummyJobQueue(), bot=DummyBot())
    await handlers.reminder_callback(update, context)

    assert query.answers == ["Не найдено"]
    assert query.edited is None
    with TestSession() as session:
        assert session.query(ReminderLog).count() == 0


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
    monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker[Session]
) -> Generator[TestClient, None, None]:
    monkeypatch.setattr(reminders, "SessionLocal", session_factory)
    monkeypatch.setattr(
        reminders,
        "compute_next",
        lambda rem, tz: datetime(2023, 1, 1, tzinfo=timezone.utc),
    )
    app = FastAPI()
    app.include_router(reminders_router, prefix="/api")
    app.dependency_overrides[require_tg_user] = lambda: {"id": 1}
    with TestClient(app) as test_client:
        yield test_client


def test_empty_returns_200(client: TestClient, session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        session.add(DbUser(telegram_id=1, thread_id="t", timezone="UTC"))
        session.commit()
    resp = client.get("/api/reminders", params={"telegramId": 1})
    assert resp.status_code == 200
    assert resp.json() == []


def test_nonempty_returns_list(client: TestClient, session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        session.add(DbUser(telegram_id=1, thread_id="t", timezone="UTC"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                title="Sugar check",
                time=time(8, 0),
                interval_hours=3,
            )
        )
        session.commit()
    resp = client.get("/api/reminders", params={"telegramId": 1})
    assert resp.status_code == 200
    assert resp.json() == [
        {
            "telegramId": 1,
            "id": 1,
            "type": "sugar",
            "title": "Sugar check",
            "kind": "at_time",
            "time": "08:00",
            "intervalHours": 3,
            "intervalMinutes": None,
            "minutesAfter": None,
            "daysOfWeek": None,
            "isEnabled": True,
            "orgId": None,
            "nextAt": "2023-01-01T00:00:00+00:00",
            "lastFiredAt": None,
            "fires7d": 0,
        }
    ]


def test_get_single_reminder(client: TestClient, session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        session.add(DbUser(telegram_id=1, thread_id="t", timezone="UTC"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                title="Sugar check",
                time=time(8, 0),
                interval_hours=3,
            )
        )
        session.commit()
    resp = client.get("/api/reminders/1", params={"telegramId": 1})
    assert resp.status_code == 200
    assert resp.json() == {
        "telegramId": 1,
        "id": 1,
        "type": "sugar",
        "title": "Sugar check",
        "kind": "at_time",
        "time": "08:00",
        "intervalHours": 3,
        "intervalMinutes": None,
        "minutesAfter": None,
        "daysOfWeek": None,
        "isEnabled": True,
        "orgId": None,
        "nextAt": "2023-01-01T00:00:00+00:00",
        "lastFiredAt": None,
        "fires7d": 0,
    }


def test_real_404(client: TestClient) -> None:
    fastapi_app = cast(FastAPI, client.app)
    fastapi_app.dependency_overrides[require_tg_user] = lambda: {"id": 2}
    resp = client.get("/api/reminders", params={"telegramId": 2})
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_single_reminder_not_found(client: TestClient, session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        session.add(DbUser(telegram_id=1, thread_id="t", timezone="UTC"))
        session.commit()
    resp = client.get("/api/reminders/1", params={"telegramId": 1})
    assert resp.status_code == 404
    assert resp.json() == {"detail": "reminder not found"}


def test_post_reminder_forbidden(client: TestClient, session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        session.add(DbUser(telegram_id=1, thread_id="t", timezone="UTC"))
        session.commit()
    fastapi_app = cast(FastAPI, client.app)
    fastapi_app.dependency_overrides[require_tg_user] = lambda: {"id": 2}
    resp = client.post(
        "/api/reminders",
        json={"telegramId": 1, "type": "sugar"},
    )
    assert resp.status_code == 403
    assert resp.json() == {"detail": "forbidden"}
    fastapi_app.dependency_overrides[require_tg_user] = lambda: {"id": 1}


def test_patch_reminder_forbidden(client: TestClient, session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        session.add(DbUser(telegram_id=1, thread_id="t", timezone="UTC"))
        session.add(
            Reminder(
                id=1,
                telegram_id=1,
                type="sugar",
                time=time(8, 0),
                is_enabled=True,
            )
        )
        session.commit()
    fastapi_app = cast(FastAPI, client.app)
    fastapi_app.dependency_overrides[require_tg_user] = lambda: {"id": 2}
    resp = client.patch(
        "/api/reminders",
        json={"telegramId": 1, "id": 1, "type": "sugar"},
    )
    assert resp.status_code == 403
    assert resp.json() == {"detail": "forbidden"}
    fastapi_app.dependency_overrides[require_tg_user] = lambda: {"id": 1}
