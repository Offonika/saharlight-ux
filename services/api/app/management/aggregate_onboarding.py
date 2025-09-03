"""Aggregate onboarding events into daily metrics.

This script can be scheduled via cron. Example (run nightly for previous day):

    5 0 * * * python -m services.api.app.management.aggregate_onboarding --date "$(date -I -d 'yesterday')"
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import date, datetime, timedelta
from typing import Iterable, Sequence, cast

from sqlalchemy import func
from sqlalchemy.orm import Session

from services.api.app.diabetes.services.db import SessionLocal, SessionMaker
from services.api.app.diabetes.services.repository import commit
from services.api.app.models.onboarding_metrics import (
    OnboardingEvent,
    OnboardingMetricDaily,
)

logger = logging.getLogger(__name__)


def _aggregate(
    session: Session, start: datetime, end: datetime
) -> Sequence[tuple[str, str, int]]:
    """Return counts of onboarding events grouped by variant and step."""

    rows = cast(
        list[tuple[str, str, int]],
        session.query(OnboardingEvent.variant, OnboardingEvent.step, func.count())
        .filter(OnboardingEvent.created_at >= start, OnboardingEvent.created_at < end)
        .group_by(OnboardingEvent.variant, OnboardingEvent.step)
        .all(),
    )
    return rows


def aggregate_for_date(
    target_date: date, *, sessionmaker: SessionMaker[Session] = SessionLocal
) -> list[dict[str, object]]:
    """Aggregate ``OnboardingEvent`` rows for ``target_date``.

    Parameters
    ----------
    target_date:
        Date for which to aggregate metrics.
    sessionmaker:
        Factory creating :class:`~sqlalchemy.orm.Session` objects. Defaults to
        ``SessionLocal`` but can be injected in tests.
    """

    start = datetime.combine(target_date, datetime.min.time())
    end = start + timedelta(days=1)

    with sessionmaker() as session:
        rows = _aggregate(session, start, end)

        session.query(OnboardingMetricDaily).filter(
            OnboardingMetricDaily.date == target_date
        ).delete()
        for variant, step, count in rows:
            session.add(
                OnboardingMetricDaily(
                    date=target_date, variant=variant, step=step, count=count
                )
            )
        commit(session)

    return [
        {"variant": variant, "step": step, "count": count}
        for variant, step, count in rows
    ]


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate onboarding events into daily metrics"
    )
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=date.today(),
        help="Target date in YYYY-MM-DD (defaults to today)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    metrics = aggregate_for_date(args.date)
    print(json.dumps(metrics, ensure_ascii=False))
    logger.info("Aggregated %d rows for %s", len(metrics), args.date)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
