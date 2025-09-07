from __future__ import annotations

import pytest

from services.api.app.config import settings
from services.api.app.diabetes.services import lesson_log
from services.api.app.diabetes.services.lesson_log import add_lesson_log


@pytest.mark.asyncio
async def test_skip_when_logging_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """add_lesson_log should no-op when feature flag is disabled."""

    monkeypatch.setattr(settings, "learning_logging_required", False)

    async def fail_run_db(*_: object, **__: object) -> None:  # pragma: no cover - sanity
        raise AssertionError("run_db should not be called")

    monkeypatch.setattr(lesson_log, "run_db", fail_run_db)

    await add_lesson_log(1, "topic", "assistant", 1, "hi")


@pytest.mark.asyncio
async def test_add_lesson_log_handles_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Errors during logging must not bubble up."""

    monkeypatch.setattr(settings, "learning_logging_required", True)

    async def fail_run_db(*_: object, **__: object) -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(lesson_log, "run_db", fail_run_db)

    await add_lesson_log(1, "topic", "assistant", 1, "hi")
