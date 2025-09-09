from __future__ import annotations

import logging
from datetime import datetime

import httpx
from pydantic import ValidationError
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

    config.reload_settings()
    base = config.get_settings().api_url
    if not base:
        await message.reply_text("❌ Не настроен API_URL")
        logger.info("billing_action=user_id:%s action=trial result=no_api_url", user.id)
        return
    trial_url = f"{base.rstrip('/')}/billing/trial"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                trial_url, params={"user_id": user.id}, timeout=10.0
            )
            resp.raise_for_status()
            try:
                data = resp.json()
            except ValueError:
                logger.exception("invalid trial response")
                await message.reply_text("❌ Ошибка сервера.")
                return
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        logger.error("billing trial failed: %s %s", exc.response.status_code, detail)
        logger.info(
            "billing_action=user_id:%s action=trial result=http_%s",
            user.id,
            exc.response.status_code,
        )
        if exc.response.status_code == 409:
            end_dt: datetime | None = None
            try:
                status_url = f"{base.rstrip('/')}/billing/status"
                async with httpx.AsyncClient() as client:
                    stat = await client.get(
                        status_url, params={"user_id": user.id}, timeout=10.0
                    )
                    stat.raise_for_status()
                    payload = stat.json()
            except httpx.HTTPError:
                logger.exception("failed to fetch trial status")
            except ValueError:
                logger.exception("invalid trial status response")
                await message.reply_text("❌ Ошибка сервера.")
                return
            else:
                sub = payload.get("subscription")
                if isinstance(sub, dict):
                    end_raw = sub.get("endDate")
                    if isinstance(end_raw, str):
                        end_dt = datetime.fromisoformat(end_raw)
            if end_dt is not None:
                end_str = end_dt.strftime("%d.%m.%Y")
                await message.reply_text(f"🎁 Пробный период уже активен до {end_str}")
            else:
                await message.reply_text("🎁 Пробный период уже активен")
            return
        await message.reply_text("❌ Не удалось активировать trial. Попробуйте позже.")
        return
    except httpx.HTTPError:
        logger.exception("failed to start trial")
        logger.info("billing_action=user_id:%s action=trial result=error", user.id)
        await message.reply_text("❌ Не удалось активировать trial. Попробуйте позже.")
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
    await message.reply_text(f"🎉 Активирован trial до {end_str}")
    kb = subscription_keyboard(False)
    if kb.inline_keyboard:
        text = (
            "🟢 Подписка PRO даёт расширенные функции:\n"
            "• Распознавание блюд по фото\n"
            "• Чат с GPT\n"
            "• Расширенные напоминания\n\n"
            "👉 Чтобы оформить подписку, нажмите кнопку ниже:"
        )
        await message.reply_text(text, reply_markup=kb)
    logger.info("billing_action=user_id:%s action=trial result=ok", user.id)


async def upgrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send information about PRO subscription with upgrade link."""

    message = update.message
    if message is None:
        return
    config.reload_settings()
    kb = subscription_keyboard(False)
    if not kb.inline_keyboard:
        await message.reply_text("❌ Не настроена ссылка на оплату.")
        logger.info(
            "billing_action=user_id:%s action=upgrade result=error",
            update.effective_user.id if update.effective_user else "?",
        )
        return
    text = (
        "🟢 Подписка PRO даёт расширенные функции:\n"
        "• Распознавание блюд по фото\n"
        "• Чат с GPT\n"
        "• Расширенные напоминания\n\n"
        "👉 Чтобы оформить подписку, нажмите кнопку ниже:"
    )
    await message.reply_text(text, reply_markup=kb)
    if update.effective_user:
        logger.info(
            "billing_action=user_id:%s action=upgrade result=ok",
            update.effective_user.id,
        )


async def subscription_button(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle "Подписка" menu button."""

    message = update.message
    user = update.effective_user
    if message is None or user is None:
        return
    config.reload_settings()
    base = config.get_settings().api_url
    if not base:
        await message.reply_text("❌ Не настроен API_URL")
        logger.info(
            "billing_action=user_id:%s action=status result=no_api_url", user.id
        )
        return
    url = f"{base.rstrip('/')}/billing/status"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params={"user_id": user.id}, timeout=10.0)
            resp.raise_for_status()
            try:
                data = resp.json()
            except ValueError:
                logger.exception("invalid billing status response")
                await message.reply_text("❌ Ошибка сервера.")
                return
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
    except ValidationError as exc:
        logger.exception("invalid billing status payload: %s", exc.errors())
        logger.info(
            "billing_action=user_id:%s action=status result=bad_payload", user.id
        )
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
            text = (
                f"Пробный период до {end_str}" if end_str else "Пробный период активен"
            )
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
