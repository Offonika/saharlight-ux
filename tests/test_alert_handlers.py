from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any, Callable, cast
from unittest.mock import AsyncMock

import pytest
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from .context_stub import AlertContext, ContextStub
import services.api.app.diabetes.handlers.alert_handlers as handlers


async def fake_get_coords_and_link() -> tuple[str | None, str | None]:
    """Return empty coordinates for tests."""
    return None, None


class DummyJob:
    def __init__(self, queue: DummyJobQueue, name: str) -> None:
        self.queue = queue
        self.name = name
        self.removed = False

    def schedule_removal(self) -> None:  # noqa: D401 - simple stub
        self.removed = True
        self.queue.jobs.remove(self)


class DummyJobQueue:
    def __init__(self) -> None:
        self.jobs: list[DummyJob] = []

    def run_once(
        self,
        callback: Callable[..., Any],
        when: Any,
        *,
        data: dict[str, object] | None = None,
        name: str | None = None,
    ) -> DummyJob:  # noqa: D401 - simple stub
        job = DummyJob(self, name or "")
        self.jobs.append(job)
        return job

    def get_jobs_by_name(self, name: str) -> list[DummyJob]:  # noqa: D401 - simple stub
        return [j for j in self.jobs if j.name == name]


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
        "SOS contact 'bad_contact' is not a Telegram username or chat id; skipping"
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


def test_schedule_alert_replaces_existing_job() -> None:
    job_queue = cast(handlers.DefaultJobQueue, DummyJobQueue())
    handlers.schedule_alert(
        1,
        job_queue,
        sugar=10.0,
        profile={},
        first_name="Ivan",
    )
    first_job = job_queue.get_jobs_by_name("alert_1")[0]
    handlers.schedule_alert(
        1,
        job_queue,
        sugar=10.0,
        profile={},
        first_name="Ivan",
    )
    jobs = job_queue.get_jobs_by_name("alert_1")
    assert len(jobs) == 1
    assert jobs[0] is not first_job
    assert first_job.removed is True
