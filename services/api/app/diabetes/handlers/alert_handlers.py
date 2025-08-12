
from __future__ import annotations

import datetime
import logging

from telegram.ext import ContextTypes

from services.api.app.diabetes.services.db import SessionLocal, Alert, Profile, run_db
from services.api.app.diabetes.handlers.common_handlers import commit_session
from services.api.app.diabetes.utils.helpers import get_coords_and_link

logger = logging.getLogger(__name__)

MAX_REPEATS = 3
ALERT_REPEAT_DELAY = datetime.timedelta(minutes=5)


def schedule_alert(user_id: int, job_queue, count: int = 1) -> None:
    job_queue.run_once(
        alert_job,
        when=ALERT_REPEAT_DELAY,
        data={"user_id": user_id, "count": count},
        name=f"alert_{user_id}",
    )


async def _send_alert_message(
    user_id: int,
    sugar: float,
    profile_info: dict,
    context: ContextTypes.DEFAULT_TYPE,
    first_name: str,
) -> None:
    coords, link = await get_coords_and_link()
    msg = f"⚠️ У {first_name} критический сахар {sugar} ммоль/л. {coords} {link}"
    await context.bot.send_message(chat_id=user_id, text=msg)
    if profile_info.get("sos_contact") and profile_info.get("sos_alerts_enabled"):
        contact = profile_info["sos_contact"]
        if contact.startswith("@"):
            await context.bot.send_message(chat_id=contact, text=msg)
        else:
            logger.info(
                "SOS contact '%s' is not a Telegram username; skipping", contact
            )


async def evaluate_sugar(
    user_id: int,
    sugar: float,
    job_queue=None,
    *,
    context: ContextTypes.DEFAULT_TYPE | None = None,
    first_name: str = "",
) -> None:
    def db_eval(session):
        profile = session.get(Profile, user_id)
        if not profile:
            return False, None
        low = profile.low_threshold
        high = profile.high_threshold

        active = (
            session.query(Alert)
            .filter_by(user_id=user_id, resolved=False)
            .all()
        )

        if (low is not None and sugar < low) or (high is not None and sugar > high):
            atype = "hypo" if low is not None and sugar < low else "hyper"
            alert = Alert(user_id=user_id, sugar=sugar, type=atype)
            session.add(alert)
            if not commit_session(session):
                return False, None
            alerts = (
                session.query(Alert)
                .filter_by(user_id=user_id, resolved=False)
                .order_by(Alert.ts.desc())
                .limit(3)
                .all()
            )
            notify = len(alerts) == 3 and all(a.type == atype for a in alerts)
            if notify:
                for a in alerts:
                    a.resolved = True
                commit_session(session)
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
            if not commit_session(session):
                return False, None
            return True, {"action": "remove", "notify": False}

    ok, result = await run_db(db_eval, sessionmaker=SessionLocal)
    if not ok or result is None:
        return
    action = result["action"]
    if action == "schedule" and job_queue is not None:
        schedule_alert(user_id, job_queue)
    elif action == "remove" and job_queue is not None:
        for job in job_queue.get_jobs_by_name(f"alert_{user_id}"):
            job.schedule_removal()

    if result.get("notify") and context is not None:
        await _send_alert_message(
            user_id, sugar, result.get("profile", {}), context, first_name
        )


async def check_alert(update, context: ContextTypes.DEFAULT_TYPE, sugar: float) -> None:
    """Wrapper to evaluate sugar using :func:`evaluate_sugar`."""
    job_queue = getattr(context, "job_queue", None)
    if job_queue is None:
        job_queue = getattr(getattr(context, "application", None), "job_queue", None)
    await evaluate_sugar(
        update.effective_user.id,
        sugar,
        job_queue,
        context=context,
        first_name=update.effective_user.first_name or "",
    )


async def alert_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    data = context.job.data
    user_id = data["user_id"]
    count = data.get("count", 1)
    with SessionLocal() as session:
        active = (
            session.query(Alert)
            .filter_by(user_id=user_id, resolved=False)
            .first()
        )
    if not active:
        return
    if count >= MAX_REPEATS:
        return
    schedule_alert(user_id, context.job_queue, count=count + 1)


async def alert_stats(update, context) -> None:
    """Отправить статистику предупреждений за последние 7 дней."""
    user_id = update.effective_user.id
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    week_ago = now - datetime.timedelta(days=7)

    with SessionLocal() as session:
        alerts = (
            session.query(Alert)
            .filter(Alert.user_id == user_id, Alert.ts >= week_ago)
            .all()
        )

    hypo = sum(1 for a in alerts if a.type == "hypo")
    hyper = sum(1 for a in alerts if a.type == "hyper")

    text = f"За 7\u202Fдн.: гипо\u202F{hypo}, гипер\u202F{hyper}"
    await update.message.reply_text(text)


