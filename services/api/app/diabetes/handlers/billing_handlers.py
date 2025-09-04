from __future__ import annotations

import logging
from datetime import datetime

import httpx
from telegram import Update
from telegram.ext import ContextTypes

from ... import config

logger = logging.getLogger(__name__)


async def trial_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Activate a 14-day trial subscription for the user."""

    message = update.message
    user = update.effective_user
    if message is None or user is None:
        return

    base = config.get_settings().api_url
    if not base:
        await message.reply_text("❌ Не настроен API_URL")
        return
    url = f"{base.rstrip('/')}/billing/trial"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, params={"user_id": user.id}, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError:
        logger.exception("failed to start trial")
        await message.reply_text(
            "❌ Не удалось активировать пробный период. Попробуйте позже."
        )
        return

    try:
        end_raw = data["endDate"]
        if not isinstance(end_raw, str):
            raise TypeError("endDate must be str")
        end_dt = datetime.fromisoformat(end_raw)
    except (KeyError, TypeError, ValueError):
        await message.reply_text(
            "❌ Ошибка сервера: неверный формат даты trial."
        )
        return
    except Exception:  # pragma: no cover - unexpected
        logger.exception("unexpected error parsing trial end date")
        await message.reply_text("❌ Ошибка сервера.")
        return
    end_str = end_dt.strftime("%d.%m.%Y")
    await message.reply_text(f"🎉 Пробный период активирован до {end_str}")


async def upgrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a link to the subscription page."""

    message = update.message
    if message is None:
        return
    try:
        url = config.build_ui_url("/subscription")
    except RuntimeError:
        await message.reply_text("❌ Не настроена ссылка на оплату.")
        return
    await message.reply_text(f"💳 Оформить подписку: {url}")


__all__ = ["trial_command", "upgrade_command"]
