from services.api.app.diabetes.services.db import Reminder, ReminderType


def test_days_of_week_roundtrip() -> None:
    reminder = Reminder(type=ReminderType.sugar)
    assert reminder.days_mask is None
    assert reminder.daysOfWeek is None

    reminder.daysOfWeek = [1, 3, 7]
    assert reminder.days_mask == (1 << 0) | (1 << 2) | (1 << 6)
    assert reminder.daysOfWeek == [1, 3, 7]

    reminder.daysOfWeek = None
    assert reminder.days_mask is None
    assert reminder.daysOfWeek is None
