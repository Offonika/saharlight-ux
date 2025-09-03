import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from services.api.app import config, reminder_events
from services.api.app.routers.reminders import ReminderError, _post_job_queue_event


@pytest.mark.asyncio
async def test_post_job_queue_event_logs_expected_errors(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    caplog.set_level(logging.ERROR)
    monkeypatch.setattr(reminder_events, "job_queue", object())
    monkeypatch.setattr(
        reminder_events,
        "notify_reminder_saved",
        AsyncMock(side_effect=ReminderError("boom")),
    )
    await _post_job_queue_event("saved", 1)
    assert any(
        "action=saved" in rec.getMessage() and "reminder_id=1" in rec.getMessage()
        for rec in caplog.records
    )


@pytest.mark.asyncio
async def test_post_job_queue_event_unexpected_error_bubbles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(reminder_events, "job_queue", object())
    monkeypatch.setattr(
        reminder_events,
        "notify_reminder_saved",
        AsyncMock(side_effect=ValueError("boom")),
    )
    with pytest.raises(ValueError):
        await _post_job_queue_event("saved", 2)


@pytest.mark.asyncio
async def test_post_job_queue_event_http_error_logs(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    caplog.set_level(logging.ERROR)
    monkeypatch.setattr(reminder_events, "job_queue", None)
    monkeypatch.setattr(
        config, "get_settings", lambda: SimpleNamespace(api_url="http://a")
    )

    async def fake_post(self: httpx.AsyncClient, url: str, json: object) -> None:  # type: ignore[override]
        raise httpx.HTTPError("boom")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post, raising=False)
    await _post_job_queue_event("deleted", 3)
    assert any(
        "action=deleted" in rec.getMessage() and "reminder_id=3" in rec.getMessage()
        for rec in caplog.records
    )
