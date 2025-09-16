"""Aggregate onboarding events into daily metrics.

This script can be scheduled via cron. Example (run nightly for previous day):

    5 0 * * * python -m services.api.app.management.aggregate_onboarding --date "$(date -I -d 'yesterday')"
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, datetime, timedelta
from typing import Iterable, Sequence, cast

import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from sqlalchemy.orm import Session

from services.api.app.diabetes.services.db import SessionLocal, SessionMaker
from services.api.app.diabetes.services.repository import commit
from services.api.app.models.onboarding_metrics import (
    OnboardingMetricEvent,
    OnboardingMetricDaily,
)

logger = logging.getLogger(__name__)


def _aggregate(session: Session, start: datetime, end: datetime) -> Sequence[tuple[str, str, int]]:
    """Return counts of onboarding events grouped by variant and step."""

    rows = cast(
        list[tuple[str, str, int]],
        session.execute(
            sa.select(
                OnboardingMetricEvent.variant,
                OnboardingMetricEvent.step,
                func.count(),
            )
            .where(
                OnboardingMetricEvent.created_at >= start,
                OnboardingMetricEvent.created_at < end,
            )
            .group_by(OnboardingMetricEvent.variant, OnboardingMetricEvent.step)
        ).all(),
    )
    return rows


def aggregate_for_date(
    target_date: date, *, sessionmaker: SessionMaker[Session] = SessionLocal
) -> list[dict[str, object]]:
    """Aggregate ``OnboardingMetricEvent`` rows for ``target_date``.

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

        session.execute(sa.delete(OnboardingMetricDaily).where(OnboardingMetricDaily.date == target_date))
        for variant, step, count in rows:
            session.add(OnboardingMetricDaily(date=target_date, variant=variant, step=step, count=count))
        commit(session)

    return [{"variant": variant, "step": step, "count": count} for variant, step, count in rows]


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate onboarding events into daily metrics")
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        default=date.today(),
        help="Target date in YYYY-MM-DD (defaults to today)",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print aggregated metrics to stdout instead of logging",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        metrics = aggregate_for_date(args.date)
    except SQLAlchemyError:
        logger.exception(
            "Database error while aggregating onboarding metrics for %s", args.date
        )
        return 1
    except (TypeError, ValueError):
        logger.exception(
            "Invalid data encountered while aggregating onboarding metrics for %s",
            args.date,
        )
        return 1
    except Exception:  # pragma: no cover - defensive programming
        logger.exception(
            "Unexpected error while aggregating onboarding metrics for %s", args.date
        )
        return 1

    metrics_json = json.dumps(metrics, ensure_ascii=False)
    if args.stdout:
        sys.stdout.write(f"{metrics_json}\n")
    else:
        logger.info("Aggregated metrics for %s: %s", args.date, metrics_json)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
