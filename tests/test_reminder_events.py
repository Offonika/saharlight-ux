from types import SimpleNamespace
from typing import cast

import pytest

from services.api.app.reminder_events import notify_reminder_saved, set_job_queue
from services.api.app.reminders.common import schedule_reminder
from services.api.app.diabetes.services.db import Reminder


def test_notify_reminder_saved_without_job_queue_raises() -> None:
    set_job_queue(None)
    with pytest.raises(RuntimeError, match="JobQueue is not initialized"):
        notify_reminder_saved(1)


def test_schedule_reminder_without_queue_raises() -> None:
    rem = cast(Reminder, SimpleNamespace(id=1, telegram_id=1, type="sugar", is_enabled=True))
    with pytest.raises(RuntimeError, match="JobQueue is not initialized"):
        schedule_reminder(rem, None, None)
