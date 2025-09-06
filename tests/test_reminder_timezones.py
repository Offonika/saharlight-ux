from __future__ import annotations

import asyncio
import datetime as dt
import inspect
from types import SimpleNamespace
from typing import Type, TypeAlias
from zoneinfo import ZoneInfo

import pytest

from services.api.app.diabetes.handlers import reminder_handlers, reminder_jobs


class _FakeJob:
    def __init__(self, name: str) -> None:
        self.name = name

    def schedule_removal(self) -> None:
        return None


class _BaseQueue:
    def __init__(self, tz: ZoneInfo) -> None:
        scheduler = SimpleNamespace(timezone=tz)
        scheduler.add_job = self._add_job  # type: ignore[attr-defined]
        self.application = SimpleNamespace(timezone=tz, scheduler=scheduler)
        self.scheduler = scheduler
        self.jobs: dict[str, list[_FakeJob]] = {}

    def get_jobs_by_name(self, name: str) -> list[_FakeJob]:
        return self.jobs.get(name, [])

    def _add_job(
        self,
        callback,
        *,
        trigger: str,
        id: str,
        name: str,
        replace_existing: bool,
        timezone: ZoneInfo,
        kwargs: dict[str, object] | None = None,
        **params: object,
    ) -> _FakeJob:
        if replace_existing:
            self.jobs.pop(name, None)
        if trigger == "cron":
            now = dt.datetime.now(timezone)
            target = dt.datetime.combine(
                now.date(), dt.time(int(params["hour"]), int(params["minute"])), tzinfo=timezone
            )
            if target <= now:
                target += dt.timedelta(days=1)
            delay = (target - now).total_seconds()
        elif trigger == "interval":
            delay = int(params["minutes"]) * 60
        else:
            delay = 0
        return self._schedule(callback, delay, kwargs.get("context") if kwargs else None, name)

    def _schedule(self, callback, delay: float, data: dict[str, object] | None, name: str | None) -> _FakeJob:
        job = _FakeJob(name or "")
        self.jobs.setdefault(name or "", []).append(job)
        asyncio.get_event_loop().create_task(self._run(callback, delay, data))
        return job

    async def _run(self, callback, delay: float, data: dict[str, object] | None) -> None:
        await asyncio.sleep(delay)
        ctx = SimpleNamespace(
            job=SimpleNamespace(data=data),
            bot=SimpleNamespace(send_message=lambda **kw: None),
        )
        if inspect.iscoroutinefunction(callback):
            await callback(ctx)
        else:
            callback(ctx)


class JobQueueV20(_BaseQueue):
    def run_once(
        self,
        callback,
        *,
        when: dt.timedelta,
        data: dict[str, object] | None = None,
        name: str | None = None,
        timezone: ZoneInfo | None = None,
        job_kwargs: dict[str, object] | None = None,
    ) -> _FakeJob:
        delay = when.total_seconds()
        return self._schedule(callback, delay, data, name)

    def run_daily(
        self,
        callback,
        *,
        time: dt.time,
        data: dict[str, object] | None = None,
        name: str | None = None,
        timezone: ZoneInfo,
        days: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6),
        job_kwargs: dict[str, object] | None = None,
    ) -> _FakeJob:
        now = dt.datetime.now(timezone)
        target = dt.datetime.combine(now.date(), time, tzinfo=timezone)
        if target <= now:
            target += dt.timedelta(days=1)
        delay = (target - now).total_seconds()
        return self._schedule(callback, delay, data, name)


class JobQueueV21(_BaseQueue):
    def run_once(
        self,
        callback,
        *,
        when: dt.timedelta,
        data: dict[str, object] | None = None,
        name: str | None = None,
        job_kwargs: dict[str, object] | None = None,
    ) -> _FakeJob:
        delay = when.total_seconds()
        return self._schedule(callback, delay, data, name)

    def run_daily(
        self,
        callback,
        *,
        time: dt.time,
        data: dict[str, object] | None = None,
        name: str | None = None,
        days: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6),
        job_kwargs: dict[str, object] | None = None,
    ) -> _FakeJob:
        tz = self.application.timezone
        now = dt.datetime.now(tz)
        target = dt.datetime.combine(now.date(), time, tzinfo=tz)
        if target <= now:
            target += dt.timedelta(days=1)
        delay = (target - now).total_seconds()
        return self._schedule(callback, delay, data, name)


QueueType: TypeAlias = Type[JobQueueV20] | Type[JobQueueV21]


@pytest.mark.parametrize("queue_cls", [JobQueueV20, JobQueueV21])
@pytest.mark.asyncio()
async def test_daily_reminder_respects_timezone(queue_cls: QueueType) -> None:
    tz = ZoneInfo("Asia/Tokyo")
    job_queue = queue_cls(tz)
    event = asyncio.Event()

    async def fake_job(context: object) -> None:
        event.set()

    original = reminder_handlers.reminder_job
    reminder_handlers.reminder_job = fake_job  # type: ignore[assignment]
    try:
        now = dt.datetime.now(tz)
        rem_time = (now + dt.timedelta(seconds=1)).time().replace(microsecond=0)
        rem = SimpleNamespace(
            id=1,
            telegram_id=1,
            type="sugar",
            time=rem_time,
            interval_hours=None,
            interval_minutes=None,
            minutes_after=None,
            kind="at_time",
            is_enabled=True,
        )
        user = SimpleNamespace(profile=SimpleNamespace(timezone="Asia/Tokyo"))
        reminder_jobs.schedule_reminder(rem, job_queue, user)
        await asyncio.wait_for(event.wait(), timeout=5)
    finally:
        reminder_handlers.reminder_job = original  # type: ignore[assignment]


@pytest.mark.parametrize("queue_cls", [JobQueueV20, JobQueueV21])
@pytest.mark.asyncio()
async def test_after_meal_reminder_respects_timezone(queue_cls: QueueType) -> None:
    tz = ZoneInfo("Asia/Tokyo")
    job_queue = queue_cls(tz)
    event = asyncio.Event()

    async def fake_job(context: object) -> None:
        event.set()

    original_job = reminder_handlers.reminder_job
    original_session = reminder_handlers.SessionLocal
    reminder_handlers.reminder_job = fake_job  # type: ignore[assignment]

    class Session:
        def __enter__(self) -> "Session":
            return self

        def __exit__(self, *exc: object) -> None:
            return None

        def scalars(self, *args: object, **kwargs: object) -> "Session":
            return self

        def filter_by(self, **kwargs: object) -> "Session":
            return self

        def all(self) -> list[object]:
            rem = SimpleNamespace(
                id=2,
                telegram_id=1,
                type="after_meal",
                time=None,
                interval_hours=None,
                interval_minutes=None,
                minutes_after=0.01,
                is_enabled=True,
                kind="after_event",
            )
            return [rem]

    reminder_handlers.SessionLocal = lambda: Session()  # type: ignore[assignment]
    try:
        reminder_handlers.schedule_after_meal(user_id=1, job_queue=job_queue)
        await asyncio.wait_for(event.wait(), timeout=5)
    finally:
        reminder_handlers.reminder_job = original_job  # type: ignore[assignment]
        reminder_handlers.SessionLocal = original_session  # type: ignore[assignment]
