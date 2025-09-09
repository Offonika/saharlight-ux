
# filename: services/api/app/diabetes/services/reminders_schedule.py
from __future__ import annotations

from datetime import date, datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo

from .db import Reminder


def _safe_combine(day: date, t: time, tz: ZoneInfo) -> datetime:
    """Создать ``datetime`` с повтором при ``nonexistent time``.

    Если ``datetime.combine`` выбрасывает ``ValueError`` (например, при переходе
    на летнее время), сдвигаем время на час вперёд и повторяем попытку.
    """

    while True:
        try:
            return datetime.combine(day, t, tzinfo=tz)
        except ValueError:
            dt = datetime.combine(day, t) + timedelta(hours=1)
            t = dt.time()


def _apply_quiet_window(dt: datetime, tz: ZoneInfo, start: str, end: str) -> datetime:
    """Если ``dt`` попадает в «тихие часы», сдвинуть на их окончание.

    Окно задаётся строками ``start``/``end`` в формате ``HH:MM`` и трактуется
    в локальной таймзоне пользователя ``tz``. Если ``start < end`` — окно внутри
    одного дня. Если ``start > end`` — окно «через полночь».
    Возвращается локальный datetime в той же таймзоне (может быть сдвинут).
    """
    local_dt = dt.astimezone(tz)

    start_time = time.fromisoformat(start)
    end_time = time.fromisoformat(end)
    start_dt = _safe_combine(local_dt.date(), start_time, tz)
    end_dt = _safe_combine(local_dt.date(), end_time, tz)

    if start_time <= end_time:
        # Обычное окно в пределах дня: [start, end)
        if start_dt <= local_dt < end_dt:
            return end_dt
    else:
        # Окно через полночь: [start, 24:00) ∪ [00:00, end)
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
    """Вычислить ближайшее срабатывание напоминания в UTC.

    - ``at_time``: ближайшее HH:MM с учётом ``days_mask`` (0 = каждый день)
    - ``every``: now + ``interval_minutes``
    - ``after_event``: планируется обработчиком события → здесь возвращаем None

    Перед возвратом применяется «тихое окно» (перенос на quiet_end, если нужно).
    """
    now_local = datetime.now(user_tz)

    # Ежедневно в конкретное время
    if rem.kind == "at_time" and rem.time is not None:
        days_mask = rem.days_mask or 0
        # Ищем в разумном окне вперёд (до двух недель)
        for offset in range(0, 14):
            day = now_local.date() + timedelta(days=offset)
            weekday = day.isoweekday()  # 1..7 (Пн..Вс)
            if days_mask == 0 or (days_mask & (1 << (weekday - 1))):
                cand_local = datetime.combine(day, rem.time, tzinfo=user_tz)
                cand_local = _apply_quiet_window(cand_local, user_tz, quiet_start, quiet_end)
                if cand_local > now_local:
                    return cand_local.astimezone(timezone.utc)
        return None

    # Через каждые N минут
    if rem.kind == "every" and rem.interval_minutes is not None:
        cand_local = now_local + timedelta(minutes=rem.interval_minutes)
        cand_local = _apply_quiet_window(cand_local, user_tz, quiet_start, quiet_end)
        return cand_local.astimezone(timezone.utc)

    # after_event планируется отдельно (после записи события)
    return None
