"""Handlers related to alert statistics."""

from __future__ import annotations

import datetime

from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import func

from diabetes.db import SessionLocal, Alert


async def alert_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display count of alerts for the last seven days grouped by type."""
    user_id = update.effective_user.id
    now = datetime.datetime.now(datetime.timezone.utc)
    week_ago = now - datetime.timedelta(days=7)
    with SessionLocal() as session:
        rows = (
            session.query(Alert.type, func.count(Alert.id))
            .filter(Alert.user_id == user_id, Alert.ts > week_ago)
            .group_by(Alert.type)
            .all()
        )
    stats = {atype: count for atype, count in rows}
    hypo = stats.get("hypo", 0)
    hyper = stats.get("hyper", 0)
    await update.message.reply_text(
        f"За 7\u202Fдн.: гипо\u202F{hypo}, гипер\u202F{hyper}"
    )


__all__ = ["alert_stats"]

