import importlib

import pytest

from services.api.app.diabetes.schemas.reminders import (
    ReminderIn,
    ReminderType,
    ScheduleKind,
)


def test_module_import() -> None:
    module = importlib.import_module("services.api.app.diabetes.schemas.reminders")
    assert hasattr(module, "ReminderIn")


def test_at_time_valid() -> None:
    reminder = ReminderIn(telegramId=1, type=ReminderType.sugar, time="08:00")
    assert reminder.kind is ScheduleKind.at_time
    assert reminder.time == "08:00"
    assert reminder.intervalMinutes is None


def test_every_interval_hours_normalization() -> None:
    reminder = ReminderIn(
        telegramId=1,
        type=ReminderType.insulin_short,
        kind=ScheduleKind.every,
        intervalHours=2,
    )
    assert reminder.intervalMinutes == 120


def test_after_event_valid() -> None:
    reminder = ReminderIn(
        telegramId=1,
        type=ReminderType.sugar,
        kind=ScheduleKind.after_event,
        minutesAfter=30,
    )
    assert reminder.minutesAfter == 30


def test_exactly_one_provided_invalid() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        ReminderIn(
            telegramId=1,
            type=ReminderType.sugar,
            time="08:00",
            intervalMinutes=10,
        )


def test_kind_requires_interval() -> None:
    with pytest.raises(ValueError, match="kind=every requires intervalMinutes"):
        ReminderIn(
            telegramId=1,
            type=ReminderType.sugar,
            kind=ScheduleKind.every,
            time="08:00",
        )


def test_kind_requires_time() -> None:
    with pytest.raises(ValueError, match="kind=at_time requires time"):
        ReminderIn(
            telegramId=1,
            type=ReminderType.sugar,
            kind=ScheduleKind.at_time,
            minutesAfter=15,
        )
