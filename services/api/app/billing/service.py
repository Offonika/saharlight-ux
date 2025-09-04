"""Billing service layer."""

from __future__ import annotations

import asyncio
import hmac
import logging
from collections.abc import Mapping

from fastapi import HTTPException

from ..schemas.billing import WebhookEvent
from .config import BillingSettings
from .providers import DummyBillingProvider


async def create_payment(settings: BillingSettings) -> dict[str, object]:
    """Create a payment using the configured provider."""

    if settings.billing_provider == "dummy":
        provider = DummyBillingProvider(test_mode=settings.billing_test_mode)
        return await provider.create_payment()
    raise HTTPException(status_code=501, detail="billing provider not supported")


async def create_checkout(settings: BillingSettings, plan: str) -> dict[str, str]:
    """Create a subscription checkout using the configured provider."""

    if settings.billing_provider == "dummy":
        provider = DummyBillingProvider(test_mode=settings.billing_test_mode)
        return await provider.create_checkout(plan)
    raise HTTPException(status_code=501, detail="billing provider not supported")


# Backward compatibility -----------------------------------------------------
create_subscription = create_checkout


async def verify_webhook(
    settings: BillingSettings,
    event: WebhookEvent,
    headers: Mapping[str, str],
    ip: str,
) -> bool:
    """Verify webhook payload using the configured provider."""

    if settings.billing_webhook_ips and ip not in settings.billing_webhook_ips:
        return False
    if not hmac.compare_digest(
        headers.get("X-Webhook-Signature") or "", event.signature
    ):
        return False
    if settings.billing_provider == "dummy":
        provider = DummyBillingProvider(
            test_mode=settings.billing_test_mode,
            webhook_secret=settings.billing_webhook_secret,
        )
    else:
        raise HTTPException(status_code=501, detail="billing provider not supported")

    try:
        return await asyncio.wait_for(
            provider.verify_webhook(event), timeout=settings.billing_webhook_timeout
        )
    except asyncio.TimeoutError:
        logger = logging.getLogger(__name__)
        logger.warning("webhook %s timeout", event.transaction_id)
        return False
