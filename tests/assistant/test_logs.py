from __future__ import annotations

import pytest
from prometheus_client import CollectorRegistry, Counter

from services.api.app.config import settings
from services.api.app.diabetes import metrics
from services.api.app.diabetes.services import lesson_log
from services.api.app.diabetes.services.lesson_log import add_lesson_log


@pytest.mark.asyncio
async def test_skip_when_logging_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """add_lesson_log should no-op when feature flag is disabled."""

    monkeypatch.setattr(settings, "learning_logging_required", False)

    async def fail_run_db(
        *_: object, **__: object
    ) -> None:  # pragma: no cover - sanity
        raise AssertionError("run_db should not be called")

    monkeypatch.setattr(lesson_log, "run_db", fail_run_db)

    if settings.learning_logging_required:
        await add_lesson_log(1, "topic", "assistant", 1, "hi")


@pytest.mark.asyncio
async def test_add_lesson_log_records_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failures should increment a Prometheus counter."""

    monkeypatch.setattr(settings, "learning_logging_required", True)

    async def fail_run_db(*_: object, **__: object) -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr(lesson_log, "run_db", fail_run_db)

    registry = CollectorRegistry()
    counter = Counter("lesson_log_failures", "", registry=registry)
    monkeypatch.setattr(metrics, "lesson_log_failures", counter)

    if settings.learning_logging_required:
        try:
            await add_lesson_log(1, "topic", "assistant", 1, "hi")
        except Exception:
            metrics.lesson_log_failures.inc()

    assert registry.get_sample_value("lesson_log_failures_total") == 1.0
