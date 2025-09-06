"""Scheduled tasks for billing subscriptions."""

from __future__ import annotations

import logging
from datetime import datetime, time as dt_time, timezone
from typing import cast

import sqlalchemy as sa
from sqlalchemy.orm import Session
from telegram.ext import ContextTypes

from services.api.app.diabetes.handlers.reminder_jobs import DefaultJobQueue
from services.api.app.diabetes.services.db import (
    Subscription,
    SubStatus,
    run_db,
)
from services.api.app.diabetes.services.repository import commit
from .log import BillingEvent, log_billing_event

logger = logging.getLogger(__name__)

_JOB_NAME = "subscriptions_expire"


def _utcnow() -> datetime:
    """Return current UTC time. Separated for easier testing."""
    return datetime.now(timezone.utc)


def schedule_subscription_expiration(jq: DefaultJobQueue) -> None:
    """Schedule daily subscription expiration check."""
    run_daily = getattr(jq, "run_daily", None)
    if not callable(run_daily):
        return
    job = run_daily(
        expire_subscriptions,
        time=dt_time(hour=0, minute=0),
        name=_JOB_NAME,
        job_kwargs={"id": _JOB_NAME, "replace_existing": True},
    )
    next_run = getattr(job, "next_run_time", None)
    logger.info("📅 scheduled %s -> next_run=%s", _JOB_NAME, next_run)


async def expire_subscriptions(_context: ContextTypes.DEFAULT_TYPE) -> None:
    """Expire outdated subscriptions."""

    def _expire(session: Session) -> list[int]:
        now = _utcnow()
        subs = session.scalars(
            sa.select(Subscription).where(
                Subscription.status.in_(
                    [
                        SubStatus.trial.value,
                        SubStatus.pending.value,
                        SubStatus.active.value,
                    ]
                ),
                sa.or_(
                    Subscription.end_date == None,  # noqa: E711
                    Subscription.end_date < now,
                ),
            )
        ).all()
        for sub in subs:
            if sub.end_date is None:
                sub.end_date = now
            if sub.status != SubStatus.trial.value:
                sub.status = cast(SubStatus, SubStatus.expired.value)
            log_billing_event(
                session,
                sub.user_id,
                BillingEvent.EXPIRED,
                {"subscription_id": sub.id},
            )
        if subs:
            commit(session)
        return [sub.user_id for sub in subs]

    user_ids = await run_db(_expire)
    for user_id in user_ids:
        logger.info("notify user %s: subscription expired", user_id)
    logger.info("expired %d subscription(s)", len(user_ids))


__all__ = ["schedule_subscription_expiration", "expire_subscriptions"]
