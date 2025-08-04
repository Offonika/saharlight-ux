from __future__ import annotations

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
