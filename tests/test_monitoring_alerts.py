from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.api.app.diabetes.services import monitoring
from services.api.app.diabetes.metrics import (
    db_down_seconds,
    get_metric_value,
    lesson_log_failures,
)


def setup_function() -> None:
    """Reset metric state before each test."""
    db_down_seconds.set(0)
    lesson_log_failures._value.set(0)  # type: ignore[attr-defined] # noqa: SLF001
    monitoring._last_lesson_log_failures = 0.0


def test_db_down_triggers_notifications(monkeypatch: pytest.MonkeyPatch) -> None:
    db_down_seconds.set(5)
    assert get_metric_value(db_down_seconds) == 5
    email = SimpleNamespace(calls=0)
    slack = SimpleNamespace(calls=0)

    def se(msg: str) -> None:
        email.calls += 1

    def ss(msg: str) -> None:
        slack.calls += 1

    monkeypatch.setattr(monitoring, "send_email", se)
    monkeypatch.setattr(monitoring, "send_slack", ss)

    monitoring.check_alerts(3)

    assert email.calls == 1
    assert slack.calls == 1


def test_lesson_log_failures_triggers_notifications(monkeypatch: pytest.MonkeyPatch) -> None:
    lesson_log_failures.inc()
    assert get_metric_value(lesson_log_failures) == 1
    email = SimpleNamespace(calls=0)
    slack = SimpleNamespace(calls=0)

    def se(msg: str) -> None:
        email.calls += 1

    def ss(msg: str) -> None:
        slack.calls += 1

    monkeypatch.setattr(monitoring, "send_email", se)
    monkeypatch.setattr(monitoring, "send_slack", ss)

    monitoring.check_alerts(3)

    assert email.calls == 1
    assert slack.calls == 1
