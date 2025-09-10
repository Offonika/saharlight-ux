import datetime

from services.api.app.diabetes.handlers.reporting_handlers import (
    _history_record_to_entry,
)
from services.api.app.diabetes.services.db import HistoryRecord


def test_history_record_to_entry_sets_utc_timezone() -> None:
    record = HistoryRecord(
        id="1",
        telegram_id=1,
        date=datetime.date(2024, 1, 1),
        time=datetime.time(12, 30),
        type="meal",
    )

    entry = _history_record_to_entry(record)

    assert entry.event_time == datetime.datetime(
        2024, 1, 1, 12, 30, tzinfo=datetime.timezone.utc
    )
