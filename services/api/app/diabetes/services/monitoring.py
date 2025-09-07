from __future__ import annotations

import logging

from ..metrics import get_metric_value, db_down_seconds, lesson_log_failures
from .db import SessionLocal, run_db

logger = logging.getLogger(__name__)


def send_email(message: str) -> None:
    """Send alert via email (placeholder)."""
    logger.info("email notification: %s", message)


def send_slack(message: str) -> None:
    """Send alert to Slack (placeholder)."""
    logger.info("slack notification: %s", message)


def notify(message: str) -> None:
    """Notify all channels."""
    send_email(message)
    send_slack(message)


_last_lesson_log_failures = 0.0


async def ping_db() -> None:
    """Ping database and update ``db_down_seconds`` gauge."""

    try:
        await run_db(lambda s: None, sessionmaker=SessionLocal)
        db_down_seconds.set(0)
    except Exception:  # pragma: no cover - logging only
        logger.exception("DB ping failed")
        db_down_seconds.inc()


def check_alerts(db_threshold: int) -> None:
    """Check metrics and notify if alerts trigger."""
    db_value = get_metric_value(db_down_seconds)
    if db_value > db_threshold:
        notify(f"db_down for {db_value} sec")
    global _last_lesson_log_failures
    current = get_metric_value(lesson_log_failures)
    if current > _last_lesson_log_failures:
        notify("lesson_log_failures increased")
    _last_lesson_log_failures = current
