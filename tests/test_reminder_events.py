import pytest

from services.api.app import reminder_events


def test_notify_without_job_queue_raises() -> None:
    reminder_events.set_job_queue(None)
    with pytest.raises(RuntimeError):
        reminder_events.notify_reminder_saved(1)
