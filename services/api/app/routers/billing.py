"""API routes for billing operations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.app.billing import (
    BillingSettings,
    create_payment,
    get_billing_settings,
)

from ..diabetes.services.db import SessionLocal, Subscription, run_db
from ..schemas.billing import BillingStatusResponse, FeatureFlags, SubscriptionSchema

router = APIRouter(prefix="/billing", tags=["Billing"])


def _require_billing_enabled(
    settings: BillingSettings = Depends(get_billing_settings),
) -> BillingSettings:
    if not settings.billing_enabled:
        raise HTTPException(status_code=503, detail="billing disabled")
    return settings


@router.post("/pay")
async def pay(
    settings: BillingSettings = Depends(_require_billing_enabled),
) -> dict[str, object]:
    """Create a payment using the configured provider."""

    return await create_payment(settings)


@router.get("/status", response_model=BillingStatusResponse)
async def status(
    user_id: int, settings: BillingSettings = Depends(get_billing_settings)
) -> BillingStatusResponse:
    """Return billing feature flags and the latest subscription for a user."""

    def _get_subscription(session: Session) -> Subscription | None:
        stmt = (
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.start_date.desc())
            .limit(1)
        )
        return session.scalars(stmt).first()

    subscription = await run_db(_get_subscription, sessionmaker=SessionLocal)
    flags = FeatureFlags(
        billingEnabled=settings.billing_enabled, paywallMode=settings.paywall_mode
    )
    if subscription is None:
        return BillingStatusResponse(featureFlags=flags, subscription=None)
    return BillingStatusResponse(
        featureFlags=flags,
        subscription=SubscriptionSchema.model_validate(
            subscription, from_attributes=True
        ),
    )
