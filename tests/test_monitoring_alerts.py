from __future__ import annotations

from types import SimpleNamespace
import os
import subprocess
import sys
from pathlib import Path

import pytest

from services.api.app.diabetes.services import monitoring
from services.api.app.diabetes.metrics import (
    db_down_seconds,
    get_metric_value,
    lesson_log_failures,
    lesson_log_failures_last,
)


def setup_function() -> None:
    """Reset metric state before each test."""
    db_down_seconds.set(0)
    lesson_log_failures._value.set(0)  # type: ignore[attr-defined] # noqa: SLF001
    lesson_log_failures_last.set(0)


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


def test_lesson_log_failures_shared_across_processes(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["PROMETHEUS_MULTIPROC_DIR"] = str(tmp_path)
    env.setdefault("PYTHONPATH", os.getcwd())
    script1 = (
        "from services.api.app.diabetes.metrics import lesson_log_failures, lesson_log_failures_last\n"
        "from services.api.app.diabetes.services import monitoring\n"
        "lesson_log_failures_last.set(0)\n"
        "lesson_log_failures.inc()\n"
        "def se(msg: str) -> None:\n    print('alert')\n"
        "def ss(msg: str) -> None:\n    pass\n"
        "monitoring.send_email = se\n"
        "monitoring.send_slack = ss\n"
        "monitoring.check_alerts(3)\n"
    )
    out1 = subprocess.run(
        [sys.executable, "-c", script1],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert out1.stdout.strip() == "alert"

    script2 = (
        "from services.api.app.diabetes.metrics import lesson_log_failures\n"
        "from services.api.app.diabetes.services import monitoring\n"
        "def se(msg: str) -> None:\n    print('alert')\n"
        "def ss(msg: str) -> None:\n    pass\n"
        "monitoring.send_email = se\n"
        "monitoring.send_slack = ss\n"
        "monitoring.check_alerts(3)\n"
        "lesson_log_failures.inc()\n"
        "monitoring.check_alerts(3)\n"
    )
    out2 = subprocess.run(
        [sys.executable, "-c", script2],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert out2.stdout.strip() == "alert"
