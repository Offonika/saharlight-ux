from __future__ import annotations

import datetime
import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, TypedDict, cast

import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes, Job, JobQueue

from services.api.app.diabetes.services.db import (
    Alert,
    Profile,
    SessionLocal as _SessionLocal,
)
from services.api.app.diabetes.services.repository import CommitError, commit as _commit
from services.api.app.diabetes.utils.helpers import get_coords_and_link
from services.api.app.diabetes.utils.jobs import schedule_once

run_db: Callable[..., Awaitable[object]]
try:
    from services.api.app.diabetes.services.db import run_db as _run_db
except ImportError as exc:  # pragma: no cover - required db runner
    raise RuntimeError("run_db is required for alert handlers") from exc
else:
    run_db = cast(Callable[..., Awaitable[object]], _run_db)

logger = logging.getLogger(__name__)

SessionLocal: sessionmaker[Session] = _SessionLocal
commit: Callable[[Session], None] = _commit

CustomContext = ContextTypes.DEFAULT_TYPE

if TYPE_CHECKING:
    DefaultJobQueue = JobQueue[ContextTypes.DEFAULT_TYPE]
else:
    DefaultJobQueue = JobQueue


class AlertJobData(TypedDict, total=False):
    user_id: int
    count: int
    sugar: float
    profile: dict[str, object]
    first_name: str


MAX_REPEATS = 3
ALERT_REPEAT_DELAY = datetime.timedelta(minutes=5)


def schedule_alert(
    user_id: int,
    job_queue: DefaultJobQueue,
    *,
    sugar: float,
    profile: dict[str, object],
    first_name: str = "",
    count: int = 1,
) -> None:
    """Schedule a follow-up sugar alert job.

    Args:
        user_id: Telegram user identifier.
        job_queue: Queue where the alert job is scheduled.
        sugar: Measured sugar level.
        profile: User profile data including SOS settings.
        first_name: User first name used in messages.
        count: Current repetition count.

    Returns:
        None.

    Side Effects:
        Enqueues :func:`alert_job` to run after ``ALERT_REPEAT_DELAY``.
    """
    data: AlertJobData = {
        "user_id": user_id,
        "count": count,
        "sugar": sugar,
        "profile": profile,
        "first_name": first_name,
    }
    schedule_once(
        job_queue,
        alert_job,
        when=ALERT_REPEAT_DELAY,
        data=data,
        name=f"alert_{user_id}",
    )


async def _send_alert_message(
    user_id: int,
    sugar: float,
    profile_info: dict[str, object],
    context: ContextTypes.DEFAULT_TYPE,
    first_name: str,
) -> None:
    """Send an alert about critical sugar to the user and SOS contact.

    Args:
        user_id: Telegram user identifier.
        sugar: Sugar level that triggered the alert.
        profile_info: Profile settings used to reach the SOS contact.
        context: Telegram context for sending messages.
        first_name: User first name for personalisation.

    Returns:
        None.

    Side Effects:
        Sends messages via the Telegram bot and logs failures.
    """
    coords, link = await get_coords_and_link()
    msg = f"⚠️ У {first_name} критический сахар {sugar} ммоль/л."
    if coords and link:
        msg += f" {coords} {link}"
    try:
        await context.bot.send_message(chat_id=user_id, text=msg)
    except TelegramError as exc:
        logger.error("Failed to send alert message to user %s: %s", user_id, exc)
    except OSError as exc:
        logger.exception("OS error sending alert message to user %s: %s", user_id, exc)
    if profile_info.get("sos_contact") and profile_info.get("sos_alerts_enabled"):
        contact_raw = profile_info["sos_contact"]
        chat_id: int | str | None
        if isinstance(contact_raw, str):
            contact = contact_raw
            if contact.startswith("@"):
                chat_id = contact
            elif contact.isdigit():
                chat_id = int(contact)
            elif contact.startswith("+") and contact.lstrip("+").isdigit():
                chat_id = int(contact.lstrip("+"))
            else:
                logger.info(
                    "SOS contact '%s' is not a Telegram username, chat id, or phone number; skipping",
                    contact,
                )
                chat_id = None
        else:
            chat_id = None
        if chat_id is not None:
            try:
                await context.bot.send_message(chat_id=chat_id, text=msg)
            except TelegramError as exc:
                logger.error(
                    "Failed to send alert message to SOS contact '%s': %s",
                    contact_raw,
                    exc,
                )
            except OSError as exc:
                logger.exception(
                    "OS error sending alert message to SOS contact '%s': %s",
                    contact_raw,
                    exc,
                )


async def evaluate_sugar(
    user_id: int,
    sugar: float,
    job_queue: DefaultJobQueue | None = None,
    *,
    context: ContextTypes.DEFAULT_TYPE | None = None,
    first_name: str = "",
) -> None:
    """Evaluate sugar level and manage alert notifications.

    Args:
        user_id: Telegram user identifier.
        sugar: Current blood sugar value.
        job_queue: Queue for scheduling repeated alerts.
        context: Telegram context used to deliver alerts.
        first_name: User first name for message formatting.

    Returns:
        None.

    Side Effects:
        Interacts with the database, schedules or removes jobs, and may send
        alert messages.
    """

    def db_eval(session: Session) -> tuple[bool, dict[str, object] | None]:
        profile = session.get(Profile, user_id)
        if not profile:
            return False, None
        low = profile.low_threshold
        high = profile.high_threshold

        active = session.scalars(sa.select(Alert).filter_by(user_id=user_id, resolved=False)).all()

        if (low is not None and sugar < low) or (high is not None and sugar > high):
            atype = "hypo" if low is not None and sugar < low else "hyper"
            alert = Alert(user_id=user_id, sugar=sugar, type=atype)
            session.add(alert)
            try:
                commit(session)
            except CommitError:
                logger.error("Failed to commit new alert for user %s", user_id)
                return False, None
            alerts = session.scalars(
                sa.select(Alert).filter_by(user_id=user_id, resolved=False).order_by(Alert.ts.desc()).limit(3)
            ).all()
            notify = len(alerts) == 3 and all(a.type == atype for a in alerts)
            if notify:
                for a in alerts:
                    a.resolved = True
                try:
                    commit(session)
                except CommitError:
                    logger.error("Failed to commit resolved alerts for user %s", user_id)
                    return False, None
            return True, {
                "action": "schedule",
                "notify": notify,
                "profile": {
                    "sos_contact": profile.sos_contact,
                    "sos_alerts_enabled": profile.sos_alerts_enabled,
                },
            }
        else:
            for a in active:
                a.resolved = True
            try:
                commit(session)
            except CommitError:
                logger.error("Failed to commit resolved alerts for user %s", user_id)
                return False, None
            return True, {"action": "remove", "notify": False}

    if run_db is None:  # pragma: no cover - guard for tests
        raise RuntimeError("run_db is unavailable")
    ok, result = cast(
        tuple[bool, dict[str, object] | None],
        await run_db(db_eval, sessionmaker=SessionLocal),
    )
    if not ok or result is None:
        return
    action = result["action"]
    if action == "schedule" and job_queue is not None:
        schedule_alert(
            user_id,
            job_queue,
            sugar=sugar,
            profile=cast(dict[str, object], result.get("profile", {})),
            first_name=first_name,
        )
    elif action == "remove" and job_queue is not None:
        for job in job_queue.get_jobs_by_name(f"alert_{user_id}"):
            if job is not None:
                job.schedule_removal()

    if result.get("notify") and context is not None:
        await _send_alert_message(
            user_id,
            sugar,
            cast(dict[str, object], result.get("profile", {})),
            context,
            first_name,
        )


async def check_alert(update: Update, context: ContextTypes.DEFAULT_TYPE, sugar: float) -> None:
    """Wrapper to evaluate sugar using :func:`evaluate_sugar`."""
    job_queue: DefaultJobQueue | None = cast(DefaultJobQueue | None, getattr(context, "job_queue", None))
    if job_queue is None:
        job_queue = cast(
            DefaultJobQueue | None,
            getattr(getattr(context, "application", None), "job_queue", None),
        )
    user = update.effective_user
    if user is None:
        return
    await evaluate_sugar(
        user.id,
        sugar,
        job_queue,
        context=context,
        first_name=user.first_name or "",
    )


async def alert_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process a scheduled alert job.

    Args:
        context: Telegram context containing job and bot.

    Returns:
        None.

    Side Effects:
        Sends alert messages, updates alert records, and reschedules or removes
        the job.
    """
    job = cast(Job[CustomContext] | None, context.job)
    if job is None:
        return
    data = cast(AlertJobData | None, job.data)
    if not data:
        job.schedule_removal()
        return
    user_id = data.get("user_id")
    sugar: float | None = data.get("sugar")
    if user_id is None or sugar is None:
        job.schedule_removal()
        return
    count: int = data.get("count", 1)
    profile: dict[str, object] = data.get("profile", {})
    first_name = data.get("first_name", "")

    def has_active_alert(session: Session) -> bool:
        return session.scalars(sa.select(Alert).filter_by(user_id=user_id, resolved=False)).first() is not None

    active = cast(
        bool,
        await run_db(has_active_alert, sessionmaker=SessionLocal),
    )
    if not active:
        job.schedule_removal()
        return
    await _send_alert_message(user_id, sugar, profile, context, first_name)
    if count >= MAX_REPEATS:

        def resolve_alerts(session: Session) -> None:
            alerts = session.scalars(sa.select(Alert).filter_by(user_id=user_id, resolved=False)).all()
            for a in alerts:
                a.resolved = True
            try:
                commit(session)
            except CommitError:
                logger.error("Failed to commit resolved alerts for user %s", user_id)

        await run_db(resolve_alerts, sessionmaker=SessionLocal)
        job.schedule_removal()
        return
    job_queue: DefaultJobQueue | None = cast(DefaultJobQueue | None, context.job_queue)
    if job_queue is None:
        return
    schedule_alert(
        user_id,
        job_queue,
        sugar=sugar,
        profile=profile,
        first_name=first_name,
        count=count + 1,
    )


async def alert_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправить статистику предупреждений за последние 7 дней."""
    user = update.effective_user
    message = update.message
    if user is None or message is None:
        return
    user_id = user.id
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    week_ago = now - datetime.timedelta(days=7)

    def fetch_alerts(session: Session) -> list[Alert]:
        return session.scalars(sa.select(Alert).where(Alert.user_id == user_id, Alert.ts >= week_ago)).all()

    alerts = cast(
        list[Alert],
        await run_db(fetch_alerts, sessionmaker=SessionLocal),
    )

    hypo = sum(1 for a in alerts if a.type == "hypo")
    hyper = sum(1 for a in alerts if a.type == "hyper")

    text = f"За 7\u202fдн.: гипо\u202f{hypo}, гипер\u202f{hyper}"
    await message.reply_text(text)


__all__ = [
    "schedule_alert",
    "evaluate_sugar",
    "check_alert",
    "alert_job",
    "alert_stats",
    "SessionLocal",
    "commit",
]
