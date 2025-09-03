"""Telegram Payments adapter for subscription billing."""

from __future__ import annotations

import logging
from dataclasses import dataclass
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

logger = logging.getLogger(__name__)


@dataclass
class TelegramPaymentsAdapter:
    """Adapter to handle Telegram Payments flow."""

    provider_token: str = settings.telegram_payments_provider_token or ""

    async def create_invoice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send an invoice to the user."""

        chat = update.effective_chat
        assert chat is not None
        chat_id = chat.id
        prices = [LabeledPrice(label="Subscription", amount=100)]
        await context.bot.send_invoice(
            chat_id=chat_id,
            title="Subscription",
            description="Monthly subscription",
            payload="subscription",
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
        payload = payment.invoice_payload
        async with httpx.AsyncClient() as client:
            await client.post(f"{api_url}/billing/webhook", json={"payload": payload})
        await msg.reply_text("✅ Платёж успешно получен")


def register_billing_handlers(
    app: Application[Any, Any, Any, Any, Any, Any],
    adapter: TelegramPaymentsAdapter | None = None,
) -> None:
    """Register Telegram Payments handlers with the application."""

    if adapter is None:
        adapter = TelegramPaymentsAdapter()
    app.add_handler(CommandHandler("subscribe", adapter.create_invoice))
    app.add_handler(PreCheckoutQueryHandler(adapter.handle_pre_checkout_query))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, adapter.handle_successful_payment))
