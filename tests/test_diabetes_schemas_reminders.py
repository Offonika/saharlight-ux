import pytest

from services.api.app.diabetes.schemas.reminders import (
    ReminderIn,
    ReminderType,
    ScheduleKind,
)


def test_time_reminder() -> None:
    reminder = ReminderIn(telegramId=1, type=ReminderType.sugar, time="08:30")
    assert reminder.kind is ScheduleKind.at_time
    assert reminder.time == "08:30"
    assert reminder.intervalMinutes is None


def test_interval_hours_normalized() -> None:
    reminder = ReminderIn(
        telegramId=1,
        type=ReminderType.sugar,
        kind=ScheduleKind.every,
        intervalHours=1,
    )
    assert reminder.intervalMinutes == 60
    assert reminder.time is None


def test_after_event_reminder() -> None:
    reminder = ReminderIn(
        telegramId=1,
        type=ReminderType.sugar,
        kind=ScheduleKind.after_event,
        minutesAfter=15,
    )
    assert reminder.minutesAfter == 15
    assert reminder.time is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"time": "08:00", "intervalMinutes": 60},
        {"kind": ScheduleKind.every, "time": "08:00"},
        {},
    ],
)
def test_invalid_reminder(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        ReminderIn(telegramId=1, type=ReminderType.sugar, **kwargs)
