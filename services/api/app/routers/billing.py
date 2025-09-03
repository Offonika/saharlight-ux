"""API routes for billing operations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.app.billing import (
    BillingSettings,
    create_payment,
    get_billing_settings,
)

from ..diabetes.services.db import (
    SessionLocal,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    run_db,
)
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


@router.post("/trial", response_model=SubscriptionSchema)
async def start_trial(user_id: int) -> SubscriptionSchema:
    """Start a trial subscription for the user."""

    now = datetime.now(timezone.utc)

    def _get_active_trial(session: Session) -> Subscription | None:
        stmt = (
            select(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.TRIAL,
                Subscription.end_date.is_not(None),
                Subscription.end_date > now,
            )
            .order_by(Subscription.start_date.desc())
            .limit(1)
        )
        return session.scalars(stmt).first()

    trial = await run_db(_get_active_trial, sessionmaker=SessionLocal)
    if trial is not None:
        return SubscriptionSchema.model_validate(trial, from_attributes=True)

    def _create_trial(session: Session) -> Subscription:
        start = now
        trial = Subscription(
            user_id=user_id,
            plan=SubscriptionPlan.PRO,
            status=SubscriptionStatus.TRIAL,
            provider="trial",
            transaction_id=str(uuid4()),
            start_date=start,
            end_date=start + timedelta(days=14),
        )
        session.add(trial)
        session.commit()
        session.refresh(trial)
        return trial

    trial = await run_db(_create_trial, sessionmaker=SessionLocal)
    return SubscriptionSchema.model_validate(trial, from_attributes=True)


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
