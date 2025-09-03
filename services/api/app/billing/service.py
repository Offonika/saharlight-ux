"""Billing service layer."""

from __future__ import annotations

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
    settings: BillingSettings, event: WebhookEvent, signature: str
) -> bool:
    """Verify webhook payload using the configured provider."""

    if settings.billing_provider == "dummy":
        provider = DummyBillingProvider(
            test_mode=settings.billing_test_mode,
            webhook_secret=settings.billing_webhook_secret,
        )
        return await provider.verify_webhook(event, signature)
    raise HTTPException(status_code=501, detail="billing provider not supported")
