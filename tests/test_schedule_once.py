from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from typing import Callable, Coroutine

import functools
import pytest

from services.api.app.diabetes.utils.jobs import JobCallback, schedule_once


async def dummy_cb(context: object) -> None:  # pragma: no cover - simple callback
    return None


class AsyncCallable:
    async def __call__(self, context: object) -> None:  # pragma: no cover - helper
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


class QueueApplicationTimezone:
    application = SimpleNamespace(
        timezone="APP", scheduler=SimpleNamespace(timezone="APP_SCH")
    )

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


class QueueWithTimezoneJobKwargs:
    timezone = "TZ"

    def run_once(
        self,
        callback: Callable[..., object],
        *,
        when: timedelta,
        data: dict[str, object] | None = None,
        name: str | None = None,
        timezone: object | None = None,
        job_kwargs: dict[str, object] | None = None,
    ) -> Job:
        self.args = SimpleNamespace(
            callback=callback,
            when=when,
            data=data,
            name=name,
            timezone=timezone,
            job_kwargs=job_kwargs,
        )
        return Job(timezone)


class QueueNoTimezoneJobKwargs:
    timezone = "TZ"

    def run_once(
        self,
        callback: Callable[..., object],
        *,
        when: timedelta,
        data: dict[str, object] | None = None,
        name: str | None = None,
        job_kwargs: dict[str, object] | None = None,
    ) -> Job:
        self.args = SimpleNamespace(
            callback=callback,
            when=when,
            data=data,
            name=name,
            timezone=None,
            job_kwargs=job_kwargs,
        )
        return Job(None)


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


def test_schedule_once_application_timezone() -> None:
    jq = QueueApplicationTimezone()
    schedule_once(jq, dummy_cb, when=timedelta(seconds=1))
    assert jq.args.timezone == jq.application.timezone


def test_schedule_once_requires_async_callback() -> None:
    jq = QueueWithTimezone()

    def sync_cb(context: object) -> None:  # pragma: no cover - test helper
        return None

    with pytest.raises(TypeError):
        schedule_once(jq, sync_cb, when=timedelta(seconds=1))


def test_schedule_once_accepts_async_callable_object() -> None:
    jq = QueueWithTimezone()
    cb_obj = AsyncCallable()
    schedule_once(jq, cb_obj, when=timedelta(seconds=1))
    assert jq.args.callback is cb_obj


@pytest.mark.parametrize(
    "queue_cls", [QueueWithTimezoneJobKwargs, QueueNoTimezoneJobKwargs]
)
def test_schedule_once_name_only_in_job_kwargs(queue_cls: type[object]) -> None:
    jq = queue_cls()
    schedule_once(
        jq,
        dummy_cb,
        when=timedelta(seconds=1),
        name="j1",
        job_kwargs={"id": "j1", "name": "j1"},
    )
    assert jq.args.name is None
    assert jq.args.job_kwargs["id"] == "j1"
    assert jq.args.job_kwargs["name"] == "j1"
    if queue_cls is QueueWithTimezoneJobKwargs:
        assert jq.args.timezone == jq.timezone
    else:
        assert jq.args.timezone is None


@pytest.mark.parametrize(
    "queue_cls", [QueueWithTimezoneJobKwargs, QueueNoTimezoneJobKwargs]
)
def test_schedule_once_adds_id_to_job_kwargs(queue_cls: type[object]) -> None:
    jq = queue_cls()
    schedule_once(
        jq,
        dummy_cb,
        when=timedelta(seconds=1),
        name="j1",
        job_kwargs={"foo": "bar"},
    )
    assert jq.args.name == "j1"
    assert jq.args.job_kwargs["id"] == "j1"
    assert "name" not in jq.args.job_kwargs
    if queue_cls is QueueWithTimezoneJobKwargs:
        assert jq.args.timezone == jq.timezone
    else:
        assert jq.args.timezone is None


class QueueWithTimezoneTypeError:
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
        raise TypeError("boom")


class QueueNoTimezoneTypeError:
    def run_once(
        self,
        callback: Callable[..., object],
        *,
        when: timedelta,
        data: dict[str, object] | None = None,
        name: str | None = None,
    ) -> Job:
        raise TypeError("boom")


def test_schedule_once_propagates_internal_type_error() -> None:
    jq = QueueWithTimezoneTypeError()
    with pytest.raises(TypeError):
        schedule_once(jq, dummy_cb, when=timedelta(seconds=1))


def test_schedule_once_propagates_internal_type_error_without_timezone() -> None:
    jq = QueueNoTimezoneTypeError()
    with pytest.raises(TypeError):
        schedule_once(jq, dummy_cb, when=timedelta(seconds=1))


async def callback_with_flag(context: object, *, flag: bool) -> None:  # pragma: no cover - helper
    return None


def decorator(
    fn: Callable[[object], Coroutine[object, object, None]]
) -> Callable[[object], Coroutine[object, object, None]]:
    @functools.wraps(fn)
    async def wrapper(*a: object, **kw: object) -> None:
        await fn(*a, **kw)

    return wrapper


partial_cb = functools.partial(callback_with_flag, flag=True)


@decorator
async def decorated_cb(context: object) -> None:  # pragma: no cover - helper
    return None


@pytest.mark.parametrize("cb", [partial_cb, decorated_cb])
def test_schedule_once_accepts_wrapped_coroutines(cb: JobCallback) -> None:
    jq = QueueWithTimezone()
    schedule_once(jq, cb, when=timedelta(seconds=1))
    assert jq.args.callback is cb
