from __future__ import annotations

import logging

import pytest
from sqlalchemy.exc import SQLAlchemyError

import services.api.app.diabetes.handlers.onboarding_handlers as onboarding


@pytest.mark.asyncio
async def test_log_event_handles_db_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    async def fail_run_db(*args: object, **kwargs: object) -> None:
        raise SQLAlchemyError("db down")

    monkeypatch.setattr(onboarding, "run_db", fail_run_db)

    with caplog.at_level(logging.ERROR):
        await onboarding._log_event(1, "evt", 1, None)
    assert "Failed to log onboarding event" in caplog.text
