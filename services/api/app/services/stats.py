from __future__ import annotations

import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..diabetes.services.db import (
    Entry as EntryDB,
    SessionLocal,
    run_db,
)
from ..schemas.stats import DayStats


async def get_day_stats(
    telegram_id: int,
    date: datetime.date | None = None,
    tz: datetime.tzinfo | None = None,
) -> DayStats | None:
    """Return aggregated stats for a given user's day.

    Data is calculated from :class:`~diabetes.services.db.Entry` records which
    store the canonical diary information.
    """
    day = date or datetime.datetime.now(tz or datetime.timezone.utc).date()

    def _query(session: Session) -> DayStats | None:
        avg_sugar, sum_bu, sum_insulin = (
            session.query(
                func.avg(EntryDB.sugar_before),
                func.sum(EntryDB.xe),
                func.sum(EntryDB.dose),
            )
            .filter(
                EntryDB.telegram_id == telegram_id,
                func.date(EntryDB.event_time) == day,
            )
            .one()
        )
        if avg_sugar is None and sum_bu is None and sum_insulin is None:
            return None
        return DayStats(
            sugar=float(avg_sugar or 0),
            breadUnits=float(sum_bu or 0),
            insulin=float(sum_insulin or 0),
        )

    return await run_db(_query, sessionmaker=SessionLocal)
