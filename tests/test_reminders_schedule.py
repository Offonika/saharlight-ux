from __future__ import annotations

from datetime import date, datetime, time, timezone, tzinfo
from zoneinfo import ZoneInfo

import pytest

from services.api.app.diabetes.services.db import Reminder
from services.api.app.diabetes.services import reminders_schedule
from services.api.app.diabetes.services.reminders_schedule import (
    _safe_combine,
    compute_next,
)


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


def test_safe_combine_skips_dst_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    tz = ZoneInfo("Europe/Berlin")
    transition_day = date(2024, 3, 31)
    real_datetime = datetime

    class GapAwareDatetime:
        calls: list[tuple[date, time, ZoneInfo | None]] = []

        @classmethod
        def combine(
            cls,
            current_day: date,
            current_time: time,
            tzinfo: ZoneInfo | None = None,
        ) -> datetime:
            cls.calls.append((current_day, current_time, tzinfo))
            if tzinfo is not None and current_time.hour == 2:
                raise ValueError("missing time")
            return real_datetime.combine(current_day, current_time, tzinfo=tzinfo)

    GapAwareDatetime.calls = []
    monkeypatch.setattr(reminders_schedule, "datetime", GapAwareDatetime)

    result = _safe_combine(transition_day, time(2, 30), tz)

    assert result == real_datetime.combine(transition_day, time(3, 30), tzinfo=tz)

    tz_calls = [
        (call_day, call_time)
        for call_day, call_time, tzinfo in GapAwareDatetime.calls
        if tzinfo is not None
    ]
    assert tz_calls == [
        (transition_day, time(2, 30)),
        (transition_day, time(3, 30)),
    ]


def test_safe_combine_raises_after_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    tz = ZoneInfo("Europe/Berlin")
    transition_day = date(2024, 3, 31)
    real_datetime = datetime

    class BrokenDatetime:
        attempts: int = 0

        @classmethod
        def combine(
            cls,
            current_day: date,
            current_time: time,
            tzinfo: ZoneInfo | None = None,
        ) -> datetime:
            if tzinfo is None:
                return real_datetime.combine(current_day, current_time)
            cls.attempts += 1
            raise ValueError("still missing")

    BrokenDatetime.attempts = 0
    monkeypatch.setattr(reminders_schedule, "datetime", BrokenDatetime)

    with pytest.raises(ValueError) as excinfo:
        _safe_combine(transition_day, time(2, 30), tz)

    message = str(excinfo.value)
    assert "2024-03-31T02:30:00" in message
    assert tz.key in message
    assert str(reminders_schedule._MAX_NONEXISTENT_SHIFT_HOURS) in message
    assert (
        BrokenDatetime.attempts
        == reminders_schedule._MAX_NONEXISTENT_SHIFT_HOURS + 1
    )

