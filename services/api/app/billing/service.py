"""Billing service layer."""

from __future__ import annotations

from fastapi import HTTPException

from .config import BillingSettings
from .providers import DummyBillingProvider


async def create_payment(settings: BillingSettings) -> dict[str, object]:
    """Create a payment using the configured provider."""

    if settings.billing_provider == "dummy":
        provider = DummyBillingProvider(test_mode=settings.billing_test_mode)
        return await provider.create_payment()
    raise HTTPException(status_code=501, detail="billing provider not supported")


async def create_subscription(settings: BillingSettings, plan: str) -> dict[str, str]:
    """Create a subscription checkout using the configured provider."""

    if settings.billing_provider == "dummy":
        provider = DummyBillingProvider(test_mode=settings.billing_test_mode)
        return await provider.create_subscription(plan)
    raise HTTPException(status_code=501, detail="billing provider not supported")
