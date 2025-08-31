from __future__ import annotations

from datetime import time as dt_time
from types import SimpleNamespace
from typing import Callable
from zoneinfo import ZoneInfo

import pytest

from services.api.app.diabetes.utils.jobs import schedule_daily


async def dummy_cb(context: object) -> None:  # pragma: no cover - simple callback
    return None


class Job:
    def __init__(self, tz: object | None) -> None:
        self.tz = tz


class QueueWithTimezone:
    timezone = ZoneInfo("Europe/Moscow")

    def run_daily(
        self,
        callback: Callable[..., object],
        *,
        time: dt_time,
        days: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6),
        data: dict[str, object] | None = None,
        name: str | None = None,
        timezone: ZoneInfo | None = None,
    ) -> Job:
        self.args = SimpleNamespace(
            callback=callback,
            time=time,
            days=days,
            data=data,
            name=name,
            timezone=timezone,
        )
        return Job(timezone)


class QueueNoTimezone:
    scheduler = SimpleNamespace(timezone=ZoneInfo("Europe/Moscow"))

    def run_daily(
        self,
        callback: Callable[..., object],
        *,
        time: dt_time,
        days: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6),
        data: dict[str, object] | None = None,
        name: str | None = None,
    ) -> Job:
        self.args = SimpleNamespace(
            callback=callback,
            time=time,
            days=days,
            data=data,
            name=name,
        )
        return Job(None)


class QueueSchedulerTimezone:
    scheduler = SimpleNamespace(timezone=ZoneInfo("Asia/Tokyo"))

    def run_daily(
        self,
        callback: Callable[..., object],
        *,
        time: dt_time,
        days: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6),
        data: dict[str, object] | None = None,
        name: str | None = None,
        timezone: ZoneInfo | None = None,
    ) -> Job:
        self.args = SimpleNamespace(
            callback=callback,
            time=time,
            days=days,
            data=data,
            name=name,
            timezone=timezone,
        )
        return Job(timezone)


class QueueApplicationTimezone:
    application = SimpleNamespace(
        timezone=ZoneInfo("Europe/Paris"),
        scheduler=SimpleNamespace(timezone=ZoneInfo("Europe/Paris")),
    )

    def run_daily(
        self,
        callback: Callable[..., object],
        *,
        time: dt_time,
        days: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6),
        data: dict[str, object] | None = None,
        name: str | None = None,
        timezone: ZoneInfo | None = None,
    ) -> Job:
        self.args = SimpleNamespace(
            callback=callback,
            time=time,
            days=days,
            data=data,
            name=name,
            timezone=timezone,
        )
        return Job(timezone)


def test_schedule_daily_uses_queue_timezone() -> None:
    jq = QueueWithTimezone()
    schedule_daily(jq, dummy_cb, time=dt_time(1, 0), data={"a": 1}, name="j1")
    assert jq.args.timezone == jq.timezone


def test_schedule_daily_without_timezone_param() -> None:
    jq = QueueNoTimezone()
    schedule_daily(jq, dummy_cb, time=dt_time(1, 0))
    assert jq.args.name is None


def test_schedule_daily_scheduler_timezone() -> None:
    jq = QueueSchedulerTimezone()
    schedule_daily(jq, dummy_cb, time=dt_time(1, 0))
    assert jq.args.timezone == jq.scheduler.timezone


def test_schedule_daily_application_timezone() -> None:
    jq = QueueApplicationTimezone()
    schedule_daily(jq, dummy_cb, time=dt_time(1, 0))
    assert jq.args.timezone == jq.application.timezone


def test_schedule_daily_requires_async_callback() -> None:
    jq = QueueWithTimezone()

    def sync_cb(context: object) -> None:  # pragma: no cover - test helper
        return None

    with pytest.raises(TypeError):
        schedule_daily(jq, sync_cb, time=dt_time(1, 0))


@pytest.mark.parametrize("queue_cls", [QueueWithTimezone, QueueNoTimezone])
def test_schedule_daily_converts_time(queue_cls: type[object]) -> None:
    tokyo = ZoneInfo("Asia/Tokyo")
    queue = queue_cls()
    t = dt_time(12, 0, tzinfo=tokyo)
    schedule_daily(queue, dummy_cb, time=t)
    assert queue.args.time == dt_time(6, 0)


def test_schedule_daily_forwards_days() -> None:
    jq = QueueWithTimezone()
    schedule_daily(jq, dummy_cb, time=dt_time(1, 0), days=(0, 2, 4))
    assert jq.args.days == (0, 2, 4)
