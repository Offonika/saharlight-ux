"""API routes for billing operations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from services.api.app.billing import (
    BillingSettings,
    create_payment,
    get_billing_settings,
)

router = APIRouter(prefix="/billing", tags=["Billing"])


def _require_billing_enabled(
    settings: BillingSettings = Depends(get_billing_settings),
) -> BillingSettings:
    if not settings.billing_enabled:
        raise HTTPException(status_code=503, detail="billing disabled")
    return settings


@router.post("/pay")
async def pay(settings: BillingSettings = Depends(_require_billing_enabled)) -> dict[str, object]:
    """Create a payment using the configured provider."""

    return await create_payment(settings)

