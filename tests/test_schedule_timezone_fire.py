from __future__ import annotations

import asyncio
import datetime as dt
from collections.abc import Awaitable, Callable
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from services.api.app.diabetes.utils.jobs import schedule_once

JobCallback = Callable[[object], Awaitable[object] | object]


class _Queue:
    def __init__(self, tz: ZoneInfo) -> None:
        self.scheduler = SimpleNamespace(timezone=tz)
        self.application = SimpleNamespace(timezone=tz, scheduler=self.scheduler)
        self.args: SimpleNamespace | None = None

    def run_once(
        self,
        callback: JobCallback,
        *,
        when: dt.datetime | dt.timedelta | float,
        data: dict[str, object] | None = None,
        name: str | None = None,
        timezone: ZoneInfo | None = None,
    ) -> object:
        self.args = SimpleNamespace(when=when, timezone=timezone)
        if isinstance(when, dt.datetime):
            now = dt.datetime.now(timezone or self.scheduler.timezone)
            target = when.astimezone(timezone or self.scheduler.timezone)
            delay = (target - now).total_seconds()
        elif isinstance(when, dt.timedelta):
            delay = when.total_seconds()
        else:
            delay = float(when)
        loop = asyncio.get_event_loop()
        ctx = SimpleNamespace(job=SimpleNamespace(data=data))
        loop.call_later(delay, lambda: asyncio.create_task(callback(ctx)))
        return SimpleNamespace()


@pytest.mark.asyncio()
async def test_schedule_once_other_timezone_fires_locally() -> None:
    moscow = ZoneInfo("Europe/Moscow")
    tokyo = ZoneInfo("Asia/Tokyo")
    jq = _Queue(moscow)
    event = asyncio.Event()

    async def cb(context: object) -> None:
        event.set()

    when_naive = dt.datetime.now(tokyo).replace(tzinfo=None) + dt.timedelta(seconds=1)
    schedule_once(jq, cb, when=when_naive, timezone=tokyo)
    assert jq.args is not None
    assert jq.args.when.tzinfo == tokyo
    await asyncio.wait_for(event.wait(), timeout=5)
