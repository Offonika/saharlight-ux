from __future__ import annotations

import logging
from typing import Callable

import pytest

from services.api.app.assistant.repositories import logs
from services.api.app.assistant.repositories.logs import add_lesson_log
from services.api.app.assistant.models import LessonLog
from services.api.app.config import settings


@pytest.mark.asyncio
async def test_add_lesson_log_warns_when_not_required(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Failures shouldn't raise when logging isn't required."""

    monkeypatch.setattr(settings, "learning_logging_required", False)

    async def fail_run_db(*_: object, **__: object) -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(logs, "run_db", fail_run_db)

    logs.pending_logs.clear()
    with caplog.at_level(logging.WARNING):
        await add_lesson_log(1, 1, 0, 1, "assistant", "hi")
    assert "Failed to flush" in caplog.text


@pytest.mark.asyncio
async def test_add_lesson_log_raises_when_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """Errors should bubble up when logging is required."""

    monkeypatch.setattr(settings, "learning_logging_required", True)

    async def fail_run_db(*_: object, **__: object) -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(logs, "run_db", fail_run_db)

    with pytest.raises(RuntimeError):
        await add_lesson_log(1, 1, 0, 1, "assistant", "hi")


@pytest.mark.asyncio
async def test_logs_queue_and_flush(monkeypatch: pytest.MonkeyPatch) -> None:
    """Queued logs are flushed once DB is available."""

    monkeypatch.setattr(settings, "learning_logging_required", False)

    logs.pending_logs.clear()

    async def fail_run_db(*_: object, **__: object) -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(logs, "run_db", fail_run_db)

    await add_lesson_log(1, 1, 0, 1, "assistant", "hi")
    await add_lesson_log(1, 1, 0, 2, "assistant", "hi")

    assert len(logs.pending_logs) == 2

    inserted: list[LessonLog] = []

    class DummySession:
        def add_all(self, objs: list[LessonLog]) -> None:
            inserted.extend(objs)

    async def ok_run_db(fn: Callable[[DummySession], None], *args: object, **kwargs: object) -> None:
        fn(DummySession())

    monkeypatch.setattr(logs, "run_db", ok_run_db)
    monkeypatch.setattr(logs, "commit", lambda _: None)

    await add_lesson_log(1, 1, 0, 3, "assistant", "hi")

    assert len(inserted) == 3
    assert not logs.pending_logs


@pytest.mark.asyncio
async def test_stop_flush_task_cancels_task() -> None:
    """stop_flush_task should cancel the background flush task."""
    await logs.stop_flush_task()  # ensure clean state
    logs.start_flush_task(0.01)
    task = logs._flush_task
    assert task is not None
    await logs.stop_flush_task()
    assert task.cancelled()
