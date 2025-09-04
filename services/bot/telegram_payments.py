"""Telegram Payments adapter for subscription billing."""

from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass
from functools import partial
from typing import Any

import httpx
from telegram import LabeledPrice, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from services.api.app.config import settings
from services.api.app.billing.config import BillingSettings

logger = logging.getLogger(__name__)


@dataclass
class TelegramPaymentsAdapter:
    """Adapter to handle Telegram Payments flow."""

    provider_token: str = settings.telegram_payments_provider_token or ""

    async def create_invoice(self, update: Update, context: ContextTypes.DEFAULT_TYPE, plan: str) -> None:
        """Send an invoice to the user."""

        chat = update.effective_chat
        assert chat is not None
        chat_id = chat.id
        prices = [LabeledPrice(label="Subscription", amount=100)]
        await context.bot.send_invoice(
            chat_id=chat_id,
            title="Subscription",
            description="Monthly subscription",
            payload=plan,
            provider_token=self.provider_token,
            currency="RUB",
            prices=prices,
        )

    async def handle_pre_checkout_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Confirm pre checkout query."""

        query = update.pre_checkout_query
        assert query is not None
        await query.answer(ok=True)

    async def handle_successful_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Notify backend about successful payment."""

        msg = update.message
        assert msg is not None
        payment = msg.successful_payment
        assert payment is not None

        api_url = settings.api_url or "http://localhost:8000"
        event_id = payment.telegram_payment_charge_id
        transaction_id = payment.provider_payment_charge_id
        plan = payment.invoice_payload

        secret = BillingSettings().billing_webhook_secret
        payload = f"{event_id}:{transaction_id}".encode()
        if secret:
            signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        else:
            signature = payload.decode()

        event = {
            "event_id": event_id,
            "transaction_id": transaction_id,
            "plan": plan,
            "signature": signature,
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{api_url}/billing/webhook",
                    json=event,
                    headers={"X-Webhook-Signature": signature},
                )
            if resp.status_code != 200:
                logger.error(
                    "billing webhook %s failed: %s %s",
                    transaction_id,
                    resp.status_code,
                    resp.text,
                )
                await msg.reply_text(
                    "⚠️ Не удалось подтвердить платёж, попробуйте позже",
                )
                return
        except httpx.HTTPError:
            logger.exception("billing webhook %s failed", transaction_id)
            await msg.reply_text(
                "⚠️ Не удалось подтвердить платёж, попробуйте позже",
            )
            return

        await msg.reply_text("✅ Платёж успешно получен")


def register_billing_handlers(
    app: Application[Any, Any, Any, Any, Any, Any],
    adapter: TelegramPaymentsAdapter | None = None,
) -> None:
    """Register Telegram Payments handlers with the application."""

    if adapter is None:
        adapter = TelegramPaymentsAdapter()
    app.add_handler(CommandHandler("subscribe", partial(adapter.create_invoice, plan="pro")))
    app.add_handler(PreCheckoutQueryHandler(adapter.handle_pre_checkout_query))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, adapter.handle_successful_payment))
