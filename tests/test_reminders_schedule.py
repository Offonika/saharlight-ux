from __future__ import annotations

from datetime import datetime, time, timezone, tzinfo
from zoneinfo import ZoneInfo

import pytest

from services.api.app.diabetes.services.db import Reminder
from services.api.app.diabetes.services import reminders_schedule
from services.api.app.diabetes.services.reminders_schedule import compute_next


def _patch_now(monkeypatch: pytest.MonkeyPatch, dt: datetime) -> None:
    class DummyDatetime(datetime):
        @classmethod
        def now(cls, tz: tzinfo | None = None) -> "DummyDatetime":
            result = dt
            if tz is not None:
                result = result.replace(tzinfo=tz)
            return result  # type: ignore[return-value]

    monkeypatch.setattr(reminders_schedule, "datetime", DummyDatetime)


def test_compute_next_at_time(monkeypatch: pytest.MonkeyPatch) -> None:
    tz = ZoneInfo("Europe/Moscow")
    _patch_now(monkeypatch, datetime(2024, 1, 1, 10, 0))
    rem = Reminder(kind="at_time", time=time(9, 0), days_mask=1)
    next_dt = compute_next(rem, tz)
    assert next_dt == datetime(2024, 1, 8, 6, 0, tzinfo=timezone.utc)


def test_compute_next_every(monkeypatch: pytest.MonkeyPatch) -> None:
    tz = ZoneInfo("Europe/Moscow")
    _patch_now(monkeypatch, datetime(2024, 1, 1, 10, 0))
    rem = Reminder(kind="every", interval_minutes=30)
    next_dt = compute_next(rem, tz)
    assert next_dt == datetime(2024, 1, 1, 7, 30, tzinfo=timezone.utc)


def test_compute_next_after_event(monkeypatch: pytest.MonkeyPatch) -> None:
    tz = ZoneInfo("UTC")
    _patch_now(monkeypatch, datetime(2024, 1, 1, 10, 0))
    rem = Reminder(kind="after_event", minutes_after=15)
    assert compute_next(rem, tz) is None



def test_quiet_window_same_day(monkeypatch: pytest.MonkeyPatch) -> None:
    tz = ZoneInfo("Europe/Moscow")
    _patch_now(monkeypatch, datetime(2024, 1, 1, 11, 0))
    rem = Reminder(kind="every", interval_minutes=60)
    next_dt = compute_next(rem, tz, quiet_start="12:00", quiet_end="14:00")
    assert next_dt == datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc)


def test_quiet_window_cross_midnight_evening(monkeypatch: pytest.MonkeyPatch) -> None:
    tz = ZoneInfo("Europe/Moscow")
    _patch_now(monkeypatch, datetime(2024, 1, 1, 22, 30))
    rem = Reminder(kind="every", interval_minutes=60)
    next_dt = compute_next(rem, tz)
    assert next_dt == datetime(2024, 1, 2, 4, 0, tzinfo=timezone.utc)


def test_quiet_window_cross_midnight_morning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tz = ZoneInfo("Europe/Moscow")
    _patch_now(monkeypatch, datetime(2024, 1, 1, 6, 20))
    rem = Reminder(kind="every", interval_minutes=30)
    next_dt = compute_next(rem, tz)
    assert next_dt == datetime(2024, 1, 1, 4, 0, tzinfo=timezone.utc)


def test_quiet_window_dst_transition(monkeypatch: pytest.MonkeyPatch) -> None:
    tz = ZoneInfo("Europe/Berlin")
    _patch_now(monkeypatch, datetime(2024, 3, 31, 2, 30))
    rem = Reminder(kind="every", interval_minutes=60)
    next_dt = compute_next(rem, tz, quiet_start="02:00", quiet_end="04:00")
    assert next_dt == datetime(2024, 3, 31, 2, 0, tzinfo=timezone.utc)

