from __future__ import annotations

from datetime import datetime, timedelta, tzinfo, timezone, time

from .db import Reminder


def _apply_quiet(
    candidate: datetime,
    quiet_start: time,
    quiet_end: time,
) -> datetime:
    """Shift ``candidate`` out of quiet hours if necessary."""
    qs = datetime.combine(candidate.date(), quiet_start, tzinfo=candidate.tzinfo)
    qe = datetime.combine(candidate.date(), quiet_end, tzinfo=candidate.tzinfo)
    if quiet_start < quiet_end:
        if qs <= candidate < qe:
            return qe
        return candidate
    # window spans midnight
    if candidate.time() >= quiet_start:
        return datetime.combine(candidate.date() + timedelta(days=1), quiet_end, tzinfo=candidate.tzinfo)
    if candidate.time() < quiet_end:
        return qe
    return candidate


def compute_next(
    rem: Reminder,
    user_tz: tzinfo,
    quiet_start: time | None = None,
    quiet_end: time | None = None,
) -> datetime | None:
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
                if quiet_start and quiet_end:
                    candidate = _apply_quiet(candidate, quiet_start, quiet_end)
                if candidate > now:
                    return candidate.astimezone(timezone.utc)
        return None

    if rem.kind == "every" and rem.interval_minutes is not None:
        candidate = now + timedelta(minutes=rem.interval_minutes)
        if quiet_start and quiet_end:
            candidate = _apply_quiet(candidate, quiet_start, quiet_end)
        return candidate.astimezone(timezone.utc)

    return None
