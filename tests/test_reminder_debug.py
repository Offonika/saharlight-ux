from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
from telegram import Update
from telegram.ext import Application, ContextTypes
from zoneinfo import ZoneInfo

from services.api.app.config import settings
import services.api.app.diabetes.handlers.reminder_debug as reminder_debug


def test_fmt_jobs_no_jobs() -> None:
    scheduler = SimpleNamespace(
        timezone=ZoneInfo("UTC"), get_jobs=Mock(return_value=[])
    )
    app = cast(
        Application, SimpleNamespace(job_queue=SimpleNamespace(scheduler=scheduler))
    )
    result = reminder_debug._fmt_jobs(app)
    assert result == "📭 Джобов нет"


def test_fmt_jobs_with_job() -> None:
    tz = ZoneInfo("Europe/Moscow")
    dt = datetime(2025, 5, 17, 12, 0, tzinfo=timezone.utc)

    class Trigger:
        def __str__(self) -> str:
            return "daily"

    job = SimpleNamespace(name="job1", id="1", next_run_time=dt, trigger=Trigger())
    scheduler = SimpleNamespace(timezone=tz, get_jobs=Mock(return_value=[job]))
    app = cast(
        Application, SimpleNamespace(job_queue=SimpleNamespace(scheduler=scheduler))
    )
    result = reminder_debug._fmt_jobs(app)
    assert (
        result == "📋 Запланированные задачи:\n"
        "• job1  (id=1)\n"
        "  next_run: 2025-05-17 15:00:00 Europe/Moscow | 2025-05-17 12:00:00 UTC\n"
        "  trigger: daily"
    )


def test_fmt_jobs_with_multiple_jobs() -> None:
    tz = ZoneInfo("Europe/Moscow")
    dt = datetime(2025, 5, 17, 12, 0, tzinfo=timezone.utc)

    class DailyTrigger:
        def __str__(self) -> str:
            return "daily"

    class WeeklyTrigger:
        def __str__(self) -> str:
            return "weekly"

    job1 = SimpleNamespace(name="job1", id="1", next_run_time=dt, trigger=DailyTrigger())
    job2 = SimpleNamespace(name="job2", id="2", next_run_time=None, trigger=WeeklyTrigger())
    scheduler = SimpleNamespace(timezone=tz, get_jobs=Mock(return_value=[job1, job2]))
    app = cast(
        Application, SimpleNamespace(job_queue=SimpleNamespace(scheduler=scheduler))
    )
    result = reminder_debug._fmt_jobs(app)
    assert (
        result == "📋 Запланированные задачи:\n"
        "• job1  (id=1)\n"
        "  next_run: 2025-05-17 15:00:00 Europe/Moscow | 2025-05-17 12:00:00 UTC\n"
        "  trigger: daily\n"
        "• job2  (id=2)\n"
        "  next_run: — | —\n"
        "  trigger: weekly"
    )


@pytest.mark.asyncio
async def test_dbg_tz_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "admin_id", 1, raising=False)
    send = AsyncMock()
    update = cast(
        Update,
        SimpleNamespace(
            effective_user=SimpleNamespace(id=1),
            effective_chat=SimpleNamespace(send_message=send),
        ),
    )
    tz = ZoneInfo("Europe/Moscow")
    context = cast(
        ContextTypes.DEFAULT_TYPE,
        SimpleNamespace(
            application=SimpleNamespace(
                job_queue=SimpleNamespace(scheduler=SimpleNamespace(timezone=tz))
            )
        ),
    )
    await reminder_debug.dbg_tz(update, context)
    assert send.call_count == 1
    assert send.call_args.args[0].startswith("🧭 TZ в планировщике: Europe/Moscow\n")


@pytest.mark.asyncio
async def test_dbg_tz_non_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "admin_id", 1, raising=False)
    send = AsyncMock()
    update = cast(
        Update,
        SimpleNamespace(
            effective_user=SimpleNamespace(id=2),
            effective_chat=SimpleNamespace(send_message=send),
        ),
    )
    context = cast(
        ContextTypes.DEFAULT_TYPE,
        SimpleNamespace(
            application=SimpleNamespace(
                job_queue=SimpleNamespace(scheduler=SimpleNamespace(timezone="UTC"))
            )
        ),
    )
    await reminder_debug.dbg_tz(update, context)
    send.assert_not_called()


@pytest.mark.asyncio
async def test_dbg_jobs_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "admin_id", 1, raising=False)
    send = AsyncMock()
    update = cast(
        Update,
        SimpleNamespace(
            effective_user=SimpleNamespace(id=1),
            effective_chat=SimpleNamespace(send_message=send),
        ),
    )
    context_app = SimpleNamespace(job_queue=SimpleNamespace(jobs=lambda: []))
    context = cast(
        ContextTypes.DEFAULT_TYPE,
        SimpleNamespace(application=context_app),
    )
    monkeypatch.setattr(reminder_debug, "_fmt_jobs", lambda app: "jobs")
    await reminder_debug.dbg_jobs(update, context)
    send.assert_awaited_once_with("jobs")


@pytest.mark.asyncio
async def test_dbg_jobs_non_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "admin_id", 1, raising=False)
    send = AsyncMock()
    update = cast(
        Update,
        SimpleNamespace(
            effective_user=SimpleNamespace(id=2),
            effective_chat=SimpleNamespace(send_message=send),
        ),
    )
    context = cast(
        ContextTypes.DEFAULT_TYPE,
        SimpleNamespace(application=SimpleNamespace()),
    )
    await reminder_debug.dbg_jobs(update, context)
    send.assert_not_called()


@pytest.mark.asyncio
async def test_dbg_ping_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "admin_id", 1, raising=False)
    send = AsyncMock()
    update = cast(
        Update,
        SimpleNamespace(
            effective_user=SimpleNamespace(id=1),
            effective_chat=SimpleNamespace(send_message=send),
        ),
    )
    context = cast(ContextTypes.DEFAULT_TYPE, SimpleNamespace())
    await reminder_debug.dbg_ping(update, context)
    send.assert_awaited_once_with("🏓 Пинг! Отправка сообщений работает ✅")


@pytest.mark.asyncio
async def test_dbg_ping_non_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "admin_id", 1, raising=False)
    send = AsyncMock()
    update = cast(
        Update,
        SimpleNamespace(
            effective_user=SimpleNamespace(id=2),
            effective_chat=SimpleNamespace(send_message=send),
        ),
    )
    context = cast(ContextTypes.DEFAULT_TYPE, SimpleNamespace())
    await reminder_debug.dbg_ping(update, context)
    send.assert_not_called()


@pytest.mark.asyncio
async def test_dbg_enqueue_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "admin_id", 1, raising=False)
    send = AsyncMock()
    run_once = Mock()
    update = cast(
        Update,
        SimpleNamespace(
            effective_user=SimpleNamespace(id=1),
            effective_chat=SimpleNamespace(id=123, send_message=send),
        ),
    )
    context = cast(
        ContextTypes.DEFAULT_TYPE,
        SimpleNamespace(
            application=SimpleNamespace(job_queue=SimpleNamespace(run_once=run_once)),
            args=["5"],
        ),
    )
    await reminder_debug.dbg_enqueue(update, context)
    run_once.assert_called_once()
    args, kwargs = run_once.call_args
    assert callable(args[0])
    assert kwargs["when"] == 5
    assert kwargs["name"] == "debug_echo_5s"
    send.assert_awaited_once_with("🧪 Поставил debug-джоб на +5s")


@pytest.mark.asyncio
async def test_dbg_enqueue_non_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "admin_id", 1, raising=False)
    send = AsyncMock()
    run_once = Mock()
    update = cast(
        Update,
        SimpleNamespace(
            effective_user=SimpleNamespace(id=2),
            effective_chat=SimpleNamespace(id=123, send_message=send),
        ),
    )
    context = cast(
        ContextTypes.DEFAULT_TYPE,
        SimpleNamespace(
            application=SimpleNamespace(job_queue=SimpleNamespace(run_once=run_once)),
            args=["5"],
        ),
    )
    await reminder_debug.dbg_enqueue(update, context)
    run_once.assert_not_called()
    send.assert_not_called()
