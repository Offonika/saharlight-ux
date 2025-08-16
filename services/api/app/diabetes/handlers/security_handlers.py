"""Handlers for security-related FAQs."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes


async def hypo_alert_faq(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Explain hypoglycemia risks and early warning benefits."""
    text = (
        "⚠️ Гипогликемия — резкое падение уровня сахара. "
        "Она может привести к головокружению, судорогам или потере сознания. "
        "Раннее предупреждение даёт шанс быстро принять углеводы и привлечь помощь, "
        "предотвращая тяжёлые последствия."
    )
    if update.message:
        await update.message.reply_text(text)


__all__ = ["hypo_alert_faq"]
