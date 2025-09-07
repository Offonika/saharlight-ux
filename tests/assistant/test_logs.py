from __future__ import annotations

import pytest

from services.api.app.config import settings
from typing import Callable

from services.api.app.diabetes.services import lesson_log
from services.api.app.diabetes.services.lesson_log import add_lesson_log
from services.api.app.diabetes.models_learning import LessonLog
from services.api.app.diabetes.metrics import lesson_log_failures


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
    """Errors during logging must not bubble up and increment metric."""

    monkeypatch.setattr(settings, "learning_logging_required", True)
    lesson_log_failures._value.set(0)  # type: ignore[attr-defined] # noqa: SLF001

    async def fail_run_db(*_: object, **__: object) -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(lesson_log, "run_db", fail_run_db)

    await add_lesson_log(1, "topic", "assistant", 1, "hi")

    assert lesson_log_failures._value.get() == 1  # type: ignore[attr-defined] # noqa: SLF001


@pytest.mark.asyncio
async def test_logs_queue_and_flush(monkeypatch: pytest.MonkeyPatch) -> None:
    """Queued logs are flushed once DB is available."""

    monkeypatch.setattr(settings, "learning_logging_required", True)

    lesson_log.pending_logs.clear()

    async def fail_run_db(*_: object, **__: object) -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(lesson_log, "run_db", fail_run_db)

    await add_lesson_log(1, "topic", "assistant", 1, "hi")
    await add_lesson_log(1, "topic", "assistant", 2, "there")

    assert len(lesson_log.pending_logs) == 2

    inserted: list[LessonLog] = []

    class DummySession:
        def add_all(self, objs: list[LessonLog]) -> None:
            inserted.extend(objs)

    async def ok_run_db(fn: Callable[[DummySession], None], *args: object, **kwargs: object) -> None:
        fn(DummySession())

    monkeypatch.setattr(lesson_log, "run_db", ok_run_db)
    monkeypatch.setattr(lesson_log, "commit", lambda _: None)

    await add_lesson_log(1, "topic", "assistant", 3, "third")

    assert len(inserted) == 3
    assert not lesson_log.pending_logs
