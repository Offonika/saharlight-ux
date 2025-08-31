from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from typing import Callable

from services.api.app.diabetes.utils.jobs import schedule_once


def dummy_cb(context: object) -> None:  # pragma: no cover - simple callback
    return None


class Job:
    def __init__(self, tz: object | None) -> None:
        self.tz = tz


class QueueWithTimezone:
    timezone = "TZ"

    def run_once(
        self,
        callback: Callable[..., object],
        *,
        when: timedelta,
        data: dict[str, object] | None = None,
        name: str | None = None,
        timezone: object | None = None,
    ) -> Job:
        self.args = SimpleNamespace(
            callback=callback, when=when, data=data, name=name, timezone=timezone
        )
        return Job(timezone)


class QueueNoTimezone:
    def run_once(
        self,
        callback: Callable[..., object],
        *,
        when: timedelta,
        data: dict[str, object] | None = None,
        name: str | None = None,
    ) -> Job:
        self.args = SimpleNamespace(callback=callback, when=when, data=data, name=name)
        return Job(None)


class QueueSchedulerTimezone:
    scheduler = SimpleNamespace(timezone="SCH")

    def run_once(
        self,
        callback: Callable[..., object],
        *,
        when: timedelta,
        data: dict[str, object] | None = None,
        name: str | None = None,
        timezone: object | None = None,
    ) -> Job:
        self.args = SimpleNamespace(
            callback=callback, when=when, data=data, name=name, timezone=timezone
        )
        return Job(timezone)


def test_schedule_once_uses_queue_timezone() -> None:
    jq = QueueWithTimezone()
    schedule_once(jq, dummy_cb, when=timedelta(seconds=1), data={"a": 1}, name="j1")
    assert jq.args.timezone == jq.timezone


def test_schedule_once_without_timezone_param() -> None:
    jq = QueueNoTimezone()
    schedule_once(jq, dummy_cb, when=timedelta(seconds=1))
    assert jq.args.name is None


def test_schedule_once_scheduler_timezone() -> None:
    jq = QueueSchedulerTimezone()
    schedule_once(jq, dummy_cb, when=timedelta(seconds=1))
    assert jq.args.timezone == jq.scheduler.timezone
