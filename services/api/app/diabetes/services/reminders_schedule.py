from __future__ import annotations

from datetime import datetime, timedelta, tzinfo, timezone

from .db import Reminder


def compute_next(rem: Reminder, user_tz: tzinfo) -> datetime | None:
    """Return next fire time for a reminder in UTC.

    Parameters
    ----------
    rem:
        Reminder instance containing scheduling info.
    user_tz:
        User's timezone.
    """
    now = datetime.now(user_tz)

    if rem.kind == "at_time" and rem.time is not None:
        days_mask = rem.days_mask or 0
        for offset in range(0, 14):
            day = now.date() + timedelta(days=offset)
            weekday = day.isoweekday()
            if days_mask == 0 or (days_mask & (1 << (weekday - 1))):
                candidate = datetime.combine(day, rem.time, tzinfo=user_tz)
                if candidate > now:
                    return candidate.astimezone(timezone.utc)
        return None

    if rem.kind == "every" and rem.interval_minutes is not None:
        return (now + timedelta(minutes=rem.interval_minutes)).astimezone(timezone.utc)

    return None
