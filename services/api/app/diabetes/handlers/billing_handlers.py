from __future__ import annotations

import logging
from datetime import datetime

import httpx
from telegram import Message, Update
from telegram.ext import ContextTypes

from ... import config
from ...schemas.billing import BillingStatusResponse
from ..utils.ui import subscription_keyboard

logger = logging.getLogger(__name__)


async def trial_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Activate a 14-day trial subscription for the user."""

    query = update.callback_query
    message: Message | None = update.message
    if query:
        await query.answer()
        if message is None and isinstance(query.message, Message):
            message = query.message
    user = update.effective_user
    if message is None or user is None:
        return

    base = config.get_settings().api_url
    if not base:
        await message.reply_text("❌ Не настроен API_URL")
        logger.info("billing_action=user_id:%s action=trial result=no_api_url", user.id)
        return
    url = f"{base.rstrip('/')}/billing/trial"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, params={"user_id": user.id}, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        logger.error("billing trial failed: %s %s", exc.response.status_code, detail)
        logger.info(
            "billing_action=user_id:%s action=trial result=http_%s",
            user.id,
            exc.response.status_code,
        )
        await message.reply_text("❌ Не удалось активировать пробный период. Попробуйте позже.")
        return
    except httpx.HTTPError:
        logger.exception("failed to start trial")
        logger.info("billing_action=user_id:%s action=trial result=error", user.id)
        await message.reply_text("❌ Не удалось активировать пробный период. Попробуйте позже.")
        return

    try:
        end_raw = data["endDate"]
        if not isinstance(end_raw, str):
            raise TypeError("endDate must be str")
        end_dt = datetime.fromisoformat(end_raw)
    except (KeyError, TypeError, ValueError):
        await message.reply_text("❌ Ошибка сервера: неверный формат даты trial.")
        return
    except Exception:  # pragma: no cover - unexpected
        logger.exception("unexpected error parsing trial end date")
        await message.reply_text("❌ Ошибка сервера.")
        return
    end_str = end_dt.strftime("%d.%m.%Y")
    await message.reply_text(f"🎉 Пробный период активирован до {end_str}")
    logger.info("billing_action=user_id:%s action=trial result=ok", user.id)


async def upgrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a link to the subscription page."""

    message = update.message
    if message is None:
        return
    try:
        url = config.build_ui_url("/subscription")
    except RuntimeError:
        await message.reply_text("❌ Не настроена ссылка на оплату.")
        logger.info(
            "billing_action=user_id:%s action=upgrade result=error",
            update.effective_user.id if update.effective_user else "?",
        )
        return
    await message.reply_text(f"💳 Оформить подписку: {url}")
    if update.effective_user:
        logger.info(
            "billing_action=user_id:%s action=upgrade result=ok",
            update.effective_user.id,
        )


async def subscription_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle "Подписка" menu button."""

    message = update.message
    user = update.effective_user
    if message is None or user is None:
        return
    base = config.get_settings().api_url
    if not base:
        await message.reply_text("❌ Не настроен API_URL")
        logger.info("billing_action=user_id:%s action=status result=no_api_url", user.id)
        return
    url = f"{base.rstrip('/')}/billing/status"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params={"user_id": user.id}, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        logger.error("billing status failed: %s %s", exc.response.status_code, detail)
        logger.info(
            "billing_action=user_id:%s action=status result=http_%s",
            user.id,
            exc.response.status_code,
        )
        await message.reply_text("❌ Не удалось получить статус. Попробуйте позже.")
        return
    except httpx.HTTPError:
        logger.exception("failed to fetch billing status")
        logger.info("billing_action=user_id:%s action=status result=error", user.id)
        await message.reply_text("❌ Не удалось получить статус. Попробуйте позже.")
        return
    try:
        status = BillingStatusResponse.model_validate(data)
    except Exception:
        logger.exception("invalid billing status payload")
        logger.info("billing_action=user_id:%s action=status result=bad_payload", user.id)
        await message.reply_text("❌ Ошибка сервера.")
        return
    sub = status.subscription
    trial_available = False
    if sub is None:
        text = "У вас нет подписки. Доступен 14-дневный trial"
        trial_available = True
    else:
        if sub.status == "trial":
            end_str = sub.endDate.strftime("%d.%m.%Y") if sub.endDate else ""
            text = f"Пробный период до {end_str}" if end_str else "Пробный период активен"
        elif sub.status == "active":
            end_str = sub.endDate.strftime("%d.%m.%Y") if sub.endDate else ""
            text = f"Подписка PRO до {end_str}" if end_str else "Подписка PRO активна"
        elif sub.status == "expired":
            text = "Подписка истекла, оформите заново"
        else:
            text = "У вас нет подписки. Доступен 14-дневный trial"
            trial_available = True
    await message.reply_text(text, reply_markup=subscription_keyboard(trial_available))
    logger.info("billing_action=user_id:%s action=status result=ok", user.id)


__all__ = ["trial_command", "upgrade_command", "subscription_button"]
