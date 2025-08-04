
from __future__ import annotations

import datetime

from telegram.ext import ContextTypes

from diabetes.db import SessionLocal, Alert, Profile
from diabetes.common_handlers import commit_session

MAX_REPEATS = 3


def schedule_alert(user_id: int, job_queue, count: int = 1) -> None:
    job_queue.run_once(
        alert_job,
        when=0,
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
            atype = "low" if low is not None and sugar < low else "high"
            alert = Alert(user_id=user_id, sugar=sugar, type=atype)
            session.add(alert)
            commit_session(session)
            schedule_alert(user_id, job_queue)
        else:
            for a in active:
                a.resolved = True
            commit_session(session)
            for job in job_queue.get_jobs_by_name(f"alert_{user_id}"):
                job.schedule_removal()


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

