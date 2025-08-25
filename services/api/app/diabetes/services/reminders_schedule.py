from __future__ import annotations

from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo

from .db import Reminder


def _apply_quiet_window(dt: datetime, tz: ZoneInfo, start: str, end: str) -> datetime:
    """Shift ``dt`` to the end of a quiet window if it falls within it.

    The window is defined by ``start`` and ``end`` strings in ``HH:MM`` format
    and interpreted in the provided timezone. When ``start`` is earlier than
    ``end`` the window lies within a single day. If ``start`` is later than
    ``end`` the window spans midnight and applies from ``start`` until ``end``
    on the following day. Datetimes outside the window are returned unchanged.
    """

    local_dt = dt.astimezone(tz)
    start_time = time.fromisoformat(start)
    end_time = time.fromisoformat(end)
    start_dt = datetime.combine(local_dt.date(), start_time, tzinfo=tz)
    end_dt = datetime.combine(local_dt.date(), end_time, tzinfo=tz)

    if start_time <= end_time:
        if start_dt <= local_dt < end_dt:
            return end_dt
    else:  # window crosses midnight
        if local_dt >= start_dt:
            return end_dt + timedelta(days=1)
        if local_dt < end_dt:
            return end_dt
    return local_dt


def compute_next(
    rem: Reminder,
    user_tz: ZoneInfo,
    quiet_start: str = "23:00",
    quiet_end: str = "07:00",
) -> datetime | None:
    """Return next fire time for a reminder in UTC.

    Parameters
    ----------
    rem:
        Reminder instance containing scheduling info.
    user_tz:
        User's timezone.
    quiet_start, quiet_end:
        Quiet hours in ``HH:MM``. The reminder will be postponed to
        ``quiet_end`` if the computed time falls inside the window.
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
                    candidate = _apply_quiet_window(candidate, user_tz, quiet_start, quiet_end)
                    return candidate.astimezone(timezone.utc)
        return None

    if rem.kind == "every" and rem.interval_minutes is not None:
        candidate = now + timedelta(minutes=rem.interval_minutes)
        candidate = _apply_quiet_window(candidate, user_tz, quiet_start, quiet_end)
        return candidate.astimezone(timezone.utc)

    return None
