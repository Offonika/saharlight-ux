from __future__ import annotations

import datetime
import logging
from types import SimpleNamespace
from typing import Any, Callable, cast
from unittest.mock import AsyncMock

import pytest
from telegram.error import TelegramError
from telegram.ext import ContextTypes, JobQueue

from .context_stub import AlertContext, ContextStub
import services.api.app.diabetes.handlers.alert_handlers as handlers


async def fake_get_coords_and_link() -> tuple[str | None, str | None]:
    """Return empty coordinates for tests."""
    return None, None


class DummyJob:
    """Minimal Job stub for testing schedule_alert."""

    def __init__(
        self,
        callback: Callable[..., object],
        when: datetime.timedelta,
        data: dict[str, object] | None,
        name: str | None,
    ) -> None:
        self.callback = callback
        self.when = when
        self.data = data
        self.name = name


class DummyJobQueue:
    """Collects jobs scheduled via run_once."""

    def __init__(self) -> None:
        self.jobs: list[DummyJob] = []

    def run_once(
        self,
        callback: Callable[..., object],
        when: datetime.timedelta,
        *,
        data: dict[str, object] | None = None,
        name: str | None = None,
        timezone: object | None = None,
    ) -> None:
        self.jobs.append(DummyJob(callback, when, data, name))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exc_cls", "expected"),
    [
        (TelegramError, "Failed to send alert message to user 1"),
        (OSError, "OS error sending alert message to user 1"),
    ],
)
async def test_send_alert_message_invalid_contact(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    exc_cls: type[BaseException],
    expected: str,
) -> None:
    """User send failures and invalid SOS contact are logged."""

    bot = SimpleNamespace(send_message=AsyncMock(side_effect=exc_cls("boom")))
    context = cast(AlertContext, ContextStub(bot=bot))
    monkeypatch.setattr(handlers, "get_coords_and_link", fake_get_coords_and_link)

    profile: dict[str, Any] = {
        "sos_contact": "bad_contact",
        "sos_alerts_enabled": True,
    }

    with caplog.at_level(logging.INFO):
        await handlers._send_alert_message(
            1,
            10.0,
            profile,
            cast(ContextTypes.DEFAULT_TYPE, context),
            "Ivan",
        )

    assert expected in caplog.text
    assert (
        "SOS contact 'bad_contact' is not a Telegram username, chat id, or phone number; skipping"
        in caplog.text
    )
    assert bot.send_message.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exc_cls", "expected"),
    [
        (
            TelegramError,
            "Failed to send alert message to SOS contact '12345'",
        ),
        (
            OSError,
            "OS error sending alert message to SOS contact '12345'",
        ),
    ],
)
async def test_send_alert_message_sos_errors(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    exc_cls: type[BaseException],
    expected: str,
) -> None:
    """Failures sending to SOS contact are logged."""

    bot = SimpleNamespace(send_message=AsyncMock(side_effect=[None, exc_cls("boom")]))
    context = cast(AlertContext, ContextStub(bot=bot))
    monkeypatch.setattr(handlers, "get_coords_and_link", fake_get_coords_and_link)

    profile: dict[str, Any] = {
        "sos_contact": "12345",
        "sos_alerts_enabled": True,
    }

    with caplog.at_level(logging.ERROR):
        await handlers._send_alert_message(
            1,
            10.0,
            profile,
            cast(ContextTypes.DEFAULT_TYPE, context),
            "Ivan",
        )

    assert expected in caplog.text
    assert bot.send_message.await_count == 2


def test_schedule_alert_schedules_job() -> None:
    """schedule_alert stores a job with expected parameters."""

    job_queue = DummyJobQueue()
    profile: dict[str, object] = {"sos_contact": "@alice"}
    handlers.schedule_alert(
        1,
        cast(JobQueue[Any], job_queue),
        sugar=10.0,
        profile=profile,
        first_name="Ivan",
        count=2,
    )
    assert len(job_queue.jobs) == 1
    job = job_queue.jobs[0]
    assert job.name == "alert_1"
    assert job.when == handlers.ALERT_REPEAT_DELAY
    assert job.data == {
        "user_id": 1,
        "count": 2,
        "sugar": 10.0,
        "profile": profile,
        "first_name": "Ivan",
    }


class DummyJobQueueNoTZ:
    """JobQueue stub without timezone parameter."""

    def __init__(self) -> None:
        self.jobs: list[DummyJob] = []

    def run_once(
        self,
        callback: Callable[..., object],
        when: datetime.timedelta,
        *,
        data: dict[str, object] | None = None,
        name: str | None = None,
    ) -> None:
        self.jobs.append(DummyJob(callback, when, data, name))


def test_schedule_alert_without_timezone_kwarg() -> None:
    """schedule_alert works when JobQueue.run_once lacks timezone param."""

    job_queue = DummyJobQueueNoTZ()
    profile: dict[str, object] = {"sos_contact": "@alice"}
    handlers.schedule_alert(
        1,
        cast(JobQueue[Any], job_queue),
        sugar=10.0,
        profile=profile,
    )
    assert len(job_queue.jobs) == 1
