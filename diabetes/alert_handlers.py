
from __future__ import annotations

import datetime
import logging

from telegram.ext import ContextTypes

from diabetes.db import SessionLocal, Alert, Profile
from diabetes.common_handlers import commit_session
from diabetes.utils import get_coords_and_link

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


def evaluate_sugar(user_id: int, sugar: float, job_queue) -> None:
    with SessionLocal() as session:
        profile = session.get(Profile, user_id)
        low = profile.low_threshold if profile else None
        high = profile.high_threshold if profile else None

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
                return
            schedule_alert(user_id, job_queue)
        else:
            for a in active:
                a.resolved = True
            if not commit_session(session):
                return
            for job in job_queue.get_jobs_by_name(f"alert_{user_id}"):
                job.schedule_removal()


async def check_alert(update, context: ContextTypes.DEFAULT_TYPE, sugar: float) -> None:
    """Evaluate sugar reading, record alerts, and notify if needed."""
    user_id = update.effective_user.id
    with SessionLocal() as session:
        profile = session.get(Profile, user_id)
        if not profile:
            return
        low = profile.low_threshold
        high = profile.high_threshold
        atype = None
        if low is not None and sugar < low:
            atype = "hypo"
        elif high is not None and sugar > high:
            atype = "hyper"
        if atype:
            alert = Alert(user_id=user_id, sugar=sugar, type=atype)
            session.add(alert)
            if not commit_session(session):
                return
            alerts = (
                session.query(Alert)
                .filter_by(user_id=user_id, resolved=False)
                .order_by(Alert.ts.desc())
                .limit(3)
                .all()
            )
            if len(alerts) == 3 and all(a.type == atype for a in alerts):
                coords, link = await get_coords_and_link()
                first_name = update.effective_user.first_name or ""
                msg = (
                    f"⚠️ У {first_name} критический сахар {sugar} ммоль/л. {coords} {link}"
                )
                await context.bot.send_message(chat_id=user_id, text=msg)
                if profile.sos_contact and profile.sos_alerts_enabled:
                    if profile.sos_contact.startswith("@"):
                        await context.bot.send_message(
                            chat_id=profile.sos_contact, text=msg
                        )
                    else:
                        logger.info(
                            "SOS contact '%s' is not a Telegram username; skipping",
                            profile.sos_contact,
                        )
                for a in alerts:
                    a.resolved = True
                commit_session(session)
        else:
            session.query(Alert).filter_by(user_id=user_id, resolved=False).update(
                {"resolved": True}
            )
            commit_session(session)


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


