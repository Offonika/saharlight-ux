from __future__ import annotations

import asyncio
import logging
from typing import Callable

import pytest

from services.api.app.assistant.repositories import logs
from services.api.app.assistant.repositories.logs import (
    add_lesson_log,
    safe_add_lesson_log,
)
from sqlalchemy.exc import IntegrityError

from services.api.app.diabetes.metrics import lesson_log_failures
from services.api.app.assistant.models import LessonLog
from services.api.app.config import settings
from services.api.app.diabetes.services.repository import CommitError


@pytest.mark.asyncio
async def test_add_lesson_log_logs_failure_when_not_required(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Failures log an error without raising when logging isn't required."""

    monkeypatch.setattr(settings, "learning_logging_required", False)

    async def fail_run_db(*_: object, **__: object) -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(logs, "run_db", fail_run_db)

    logs.pending_logs.clear()
    lesson_log_failures._value.set(0)  # type: ignore[attr-defined] # noqa: SLF001

    try:
        with caplog.at_level(logging.ERROR):
            await add_lesson_log(1, 1, 0, 1, "assistant", "hi")

        assert "flush_pending_logs failed" in caplog.text
        assert len(logs.pending_logs) == 1
        assert lesson_log_failures._value.get() == 1  # type: ignore[attr-defined]
    finally:
        logs.pending_logs.clear()
        lesson_log_failures._value.set(0)  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_add_lesson_log_raises_when_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Errors should bubble up when logging is required."""

    monkeypatch.setattr(settings, "learning_logging_required", True)

    async def fail_run_db(*_: object, **__: object) -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(logs, "run_db", fail_run_db)

    with pytest.raises(RuntimeError):
        await add_lesson_log(1, 1, 0, 1, "assistant", "hi")


@pytest.mark.asyncio
async def test_safe_add_lesson_log_handles_failure_not_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """safe_add_lesson_log returns False and keeps state when logging optional."""

    monkeypatch.setattr(settings, "learning_logging_required", False)

    async def fail_run_db(*_: object, **__: object) -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(logs, "run_db", fail_run_db)
    logs.pending_logs.clear()
    lesson_log_failures._value.set(0)  # type: ignore[attr-defined] # noqa: SLF001

    ok = await safe_add_lesson_log(1, 1, 0, 1, "assistant", "hi")

    assert ok is False
    assert len(logs.pending_logs) == 1
    assert lesson_log_failures._value.get() == 1  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_safe_add_lesson_log_logs_when_required(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """safe_add_lesson_log logs and alerts when logging is required."""

    monkeypatch.setattr(settings, "learning_logging_required", True)

    async def fail_run_db(*_: object, **__: object) -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(logs, "run_db", fail_run_db)

    called = False

    def fake_notify(message: str) -> None:
        nonlocal called
        called = True
        assert message

    monkeypatch.setattr(logs, "notify", fake_notify)

    with caplog.at_level(logging.ERROR):
        ok = await safe_add_lesson_log(1, 1, 0, 1, "assistant", "hi")

    assert ok is False
    assert called is True
    assert "Failed to add lesson log" in caplog.text


@pytest.mark.asyncio
async def test_safe_add_lesson_log_requeues_on_commit_integrity_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Commit failures should keep logs queued for future retries."""

    monkeypatch.setattr(settings, "learning_logging_required", False)

    async def fail_run_db(*_: object, **__: object) -> None:
        integrity_exc = IntegrityError("stmt", {}, Exception("boom"))
        raise CommitError() from integrity_exc

    monkeypatch.setattr(logs, "run_db", fail_run_db)

    logs.pending_logs.clear()
    lesson_log_failures._value.set(0)  # type: ignore[attr-defined] # noqa: SLF001

    try:
        results = []
        for step_idx in range(3):
            ok = await safe_add_lesson_log(1, 1, 0, step_idx, "assistant", f"hi-{step_idx}")
            results.append(ok)

        assert results == [False, False, False]
        assert len(logs.pending_logs) == 3
        assert {log.step_idx for log in logs.pending_logs} == {0, 1, 2}
        assert lesson_log_failures._value.get() == 6  # type: ignore[attr-defined]
    finally:
        logs.pending_logs.clear()
        lesson_log_failures._value.set(0)  # type: ignore[attr-defined]


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

        def get(self, *args: object, **kwargs: object) -> object | None:
            return object()

    async def ok_run_db(
        fn: Callable[[DummySession], None], *args: object, **kwargs: object
    ) -> None:
        fn(DummySession())

    monkeypatch.setattr(logs, "run_db", ok_run_db)
    monkeypatch.setattr(logs, "commit", lambda _: None)

    await add_lesson_log(1, 1, 0, 3, "assistant", "hi")

    assert len(inserted) == 3
    assert not logs.pending_logs


@pytest.mark.asyncio
async def test_flush_does_not_block_new_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Logs enqueued during a flush should not block or be lost."""

    logs.pending_logs.clear()

    inserted: list[LessonLog] = []

    class DummySession:
        def add_all(self, objs: list[LessonLog]) -> None:
            inserted.extend(objs)

        def get(self, *args: object, **kwargs: object) -> object | None:
            return object()

    flush_started = asyncio.Event()
    continue_flush = asyncio.Event()
    calls = 0

    async def slow_run_db(
        fn: Callable[[DummySession], None], *args: object, **kwargs: object
    ) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            flush_started.set()
            await continue_flush.wait()
        fn(DummySession())

    monkeypatch.setattr(logs, "run_db", slow_run_db)
    monkeypatch.setattr(logs, "commit", lambda _: None)

    first = asyncio.create_task(add_lesson_log(1, 1, 0, 1, "assistant", "hi"))
    await flush_started.wait()

    assert not first.done()

    await add_lesson_log(1, 1, 0, 2, "assistant", "hi")

    assert not first.done()
    assert len(inserted) == 1
    assert inserted[0].step_idx == 2

    continue_flush.set()
    await first

    assert {log.step_idx for log in inserted} == {1, 2}
    assert not logs.pending_logs


@pytest.mark.asyncio
async def test_stop_flush_task_cancels_task() -> None:
    """stop_flush_task should cancel the background flush task."""
    await logs.stop_flush_task()  # ensure clean state
    await logs.start_flush_task_async(0.01)
    task = logs._flush_task
    assert task is not None
    await logs.stop_flush_task()
    assert task.cancelled()


@pytest.mark.asyncio
async def test_start_flush_task_restarts_on_failure(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """start_flush_task should log and restart on background failures."""

    await logs.stop_flush_task()

    calls = 0

    async def fail_once(_: float) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("boom")
        await asyncio.sleep(0.01)

    monkeypatch.setattr(logs, "_flush_periodically", fail_once)

    with caplog.at_level(logging.ERROR):
        logs.start_flush_task(0.01)
        first = logs._flush_task
        assert first is not None
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        second = logs._flush_task
        assert second is not None
        assert second is not first
        assert "Background flush task failed" in caplog.text

    await logs.stop_flush_task()


@pytest.mark.asyncio
async def test_pending_logs_respects_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Oldest logs are dropped when the queue reaches the configured limit."""

    monkeypatch.setattr(settings, "learning_logging_required", False)
    monkeypatch.setattr(logs, "PENDING_LOG_LIMIT", 2)

    async def fail_run_db(*_: object, **__: object) -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(logs, "run_db", fail_run_db)
    logs.pending_logs.clear()

    await add_lesson_log(1, 1, 0, 1, "assistant", "a")
    await add_lesson_log(1, 1, 0, 2, "assistant", "b")
    await add_lesson_log(1, 1, 0, 3, "assistant", "c")

    assert [log.step_idx for log in logs.pending_logs] == [2, 3]


def test_start_flush_task_without_loop(caplog: pytest.LogCaptureFixture) -> None:
    """start_flush_task should skip when no event loop is running."""

    logs._flush_task = None
    with caplog.at_level(logging.INFO):
        logs.start_flush_task()
    assert logs._flush_task is None
    assert "No running event loop" in caplog.text
