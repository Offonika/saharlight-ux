from __future__ import annotations

import pytest
from fastapi import HTTPException

from services.api.app.billing import service
from services.api.app.billing.config import BillingSettings
from services.api.app.billing.providers.dummy import DummyBillingProvider


@pytest.mark.asyncio
async def test_create_payment_unknown_provider() -> None:
    settings = BillingSettings(BILLING_PROVIDER="other")
    with pytest.raises(HTTPException):
        await service.create_payment(settings)


@pytest.mark.asyncio
async def test_create_subscription_unknown_provider() -> None:
    settings = BillingSettings(BILLING_PROVIDER="other")
    with pytest.raises(HTTPException):
        await service.create_subscription(settings, "pro")


@pytest.mark.asyncio
async def test_dummy_provider_methods() -> None:
    provider = DummyBillingProvider(test_mode=False)
    payment = await provider.create_payment()
    assert payment == {"status": "ok", "test_mode": False}
    checkout = await provider.create_subscription("pro")
    assert checkout["url"].startswith("https://dummy/pro/")
