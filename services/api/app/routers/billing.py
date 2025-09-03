"""API routes for billing operations."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.app.billing import (
    BillingSettings,
    create_payment,
    create_subscription,
    get_billing_settings,
)

from ..diabetes.services.db import (
    SessionLocal,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
    run_db,
)
from ..schemas.billing import (
    BillingStatusResponse,
    CheckoutSchema,
    FeatureFlags,
    SubscriptionSchema,
    WebhookEvent,
)

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


@router.post("/subscribe", response_model=CheckoutSchema)
async def subscribe(
    user_id: int,
    plan: SubscriptionPlan,
    settings: BillingSettings = Depends(_require_billing_enabled),
) -> CheckoutSchema:
    """Initiate a subscription and return checkout details."""

    checkout = await create_subscription(settings, plan)
    now = datetime.now(timezone.utc)

    def _create_draft(session: Session) -> None:
        draft = Subscription(
            user_id=user_id,
            plan=plan,
            status=SubscriptionStatus.PENDING,
            provider=settings.billing_provider,
            transaction_id=checkout["id"],
            start_date=now,
            end_date=None,
        )
        session.add(draft)
        session.commit()

    await run_db(_create_draft, sessionmaker=SessionLocal)
    return CheckoutSchema.model_validate(checkout)


@router.post("/webhook")
async def webhook(
    event: WebhookEvent,
    settings: BillingSettings = Depends(_require_billing_enabled),
) -> dict[str, str]:
    """Process provider webhook and activate subscription."""

    logger = logging.getLogger(__name__)
    if settings.billing_provider != "dummy":
        raise HTTPException(status_code=501, detail="billing provider not supported")

    expected_sig = f"{event.event_id}:{event.transaction_id}"
    if event.signature != expected_sig:
        logger.info("webhook %s invalid_signature", event.event_id)
        raise HTTPException(status_code=400, detail="invalid signature")

    now = datetime.now(timezone.utc)

    def _activate(session: Session) -> bool:
        stmt = select(Subscription).where(
            Subscription.transaction_id == event.transaction_id
        )
        sub = session.scalars(stmt).first()
        if sub is None:
            return False
        sub_end = sub.end_date
        if sub_end is not None and sub_end.tzinfo is None:
            sub_end = sub_end.replace(tzinfo=timezone.utc)
        if (
            sub.status == SubscriptionStatus.ACTIVE
            and sub_end is not None
            and sub_end > now
        ):
            return False
        base = sub_end if sub_end is not None and sub_end > now else now
        sub.plan = event.plan
        sub.status = SubscriptionStatus.ACTIVE
        sub.end_date = base + timedelta(days=30)
        session.commit()
        return True

    updated = await run_db(_activate, sessionmaker=SessionLocal)
    status = "processed" if updated else "ignored"
    logger.info("webhook %s %s", event.event_id, status)
    return {"status": status}


@router.post("/mock-webhook/{checkout_id}")
async def mock_webhook(
    checkout_id: str,
    settings: BillingSettings = Depends(_require_billing_enabled),
) -> dict[str, str]:
    """Simulate provider webhook to activate a subscription in test mode."""

    if not settings.billing_test_mode:
        raise HTTPException(status_code=403, detail="test mode disabled")

    def _activate(session: Session) -> bool:
        stmt = select(Subscription).where(Subscription.transaction_id == checkout_id)
        sub = session.scalars(stmt).first()
        if sub is None:
            return False
        sub.status = SubscriptionStatus.ACTIVE
        session.commit()
        return True

    updated = await run_db(_activate, sessionmaker=SessionLocal)
    if not updated:
        raise HTTPException(status_code=404, detail="subscription not found")
    return {"status": "ok"}


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
