"""API routes for billing operations."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from psycopg2.errors import InvalidTextRepresentation

from services.api.app.billing import (
    BillingEvent,
    BillingSettings,
    create_checkout,
    create_payment,
    get_billing_settings,
    log_billing_event,
    verify_webhook,
)
from services.api.app.billing.config import BillingProvider

from ..diabetes.services.db import (
    SessionLocal,
    Subscription,
    SubscriptionPlan,
    SubStatus,
    run_db,
)
from ..schemas.billing import (
    BillingStatusResponse,
    CheckoutSchema,
    DummyCheckoutSchema,
    FeatureFlags,
    SubscriptionSchema,
    WebhookEvent,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])


def _get_active_trial(
    session: Session,
    *,
    user_id: int,
    for_update: bool = False,
) -> Subscription | None:
    stmt = (
        select(Subscription)
        .where(
            Subscription.user_id == user_id,
            Subscription.status == SubStatus.trial.value,
        )
        .order_by(Subscription.start_date.desc())
        .limit(1)
    )
    if for_update:
        stmt = stmt.with_for_update()
    return session.scalars(stmt).first()


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
async def start_trial(
    user_id: int,
    settings: BillingSettings = Depends(_require_billing_enabled),
) -> SubscriptionSchema:
    """Start a trial subscription for the user."""

    now = datetime.now(timezone.utc)

    def _create_trial(session: Session) -> Subscription:
        start = now
        trial = Subscription(
            user_id=user_id,
            plan=SubscriptionPlan.PRO,
            status=cast(SubStatus, SubStatus.trial.value),
            provider="trial",
            transaction_id=str(uuid4()),
            start_date=start,
            end_date=start + timedelta(days=14),
        )
        session.add(trial)
        log_billing_event(
            session,
            user_id,
            BillingEvent.INIT,
            {"plan": SubscriptionPlan.PRO.value, "source": "trial"},
        )
        return trial

    def _get_or_create(session: Session) -> Subscription:
        with session.begin():
            stmt = (
                select(Subscription)
                .where(
                    Subscription.user_id == user_id,
                    Subscription.status.in_(
                        [SubStatus.trial.value, SubStatus.active.value]
                    ),
                )
                .order_by(Subscription.start_date.desc())
                .limit(1)
                .with_for_update()
            )
            existing = session.scalars(stmt).first()
            if existing is not None:
                status = SubStatus(existing.status)
                if status is SubStatus.trial:
                    raise HTTPException(status_code=409, detail="Trial already active")
                raise HTTPException(
                    status_code=409, detail="subscription already active"
                )
            return _create_trial(session)

    trial: Subscription | None
    try:
        trial = await run_db(_get_or_create, sessionmaker=SessionLocal)
    except HTTPException as exc:
        if exc.status_code == 409:
            logger.info("subscription already active", extra={"user_id": user_id})
        raise
    except InvalidTextRepresentation as exc:
        params = getattr(exc, "params", None)
        logger.warning(
            "trial creation failed",
            extra={
                "user_id": user_id,
                "status": SubStatus.trial.value,
                "plan": SubscriptionPlan.PRO.value,
                "params": params,
            },
            exc_info=exc,
        )
        raise HTTPException(status_code=400, detail="invalid enum value") from exc
    except IntegrityError as exc:
        logger.warning(
            "trial creation failed",
            extra={
                "user_id": user_id,
                "status": SubStatus.trial.value,
                "plan": SubscriptionPlan.PRO.value,
                "params": exc.params,
            },
            exc_info=exc,
        )
        raise HTTPException(status_code=409, detail="Trial already active") from exc
    if trial is None:
        raise HTTPException(status_code=500, detail="trial retrieval failed")

    return SubscriptionSchema.model_validate(trial, from_attributes=True)


@router.post("/subscribe", response_model=CheckoutSchema | DummyCheckoutSchema)
async def subscribe(
    user_id: int,
    plan: SubscriptionPlan,
    settings: BillingSettings = Depends(_require_billing_enabled),
) -> CheckoutSchema | DummyCheckoutSchema:
    """Initiate a subscription and return checkout details."""

    now = datetime.now(timezone.utc)

    def _ensure_no_active(session: Session) -> None:
        stmt = select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.status.in_([SubStatus.trial.value, SubStatus.active.value]),
        )
        if session.scalars(stmt).first() is not None:
            raise HTTPException(status_code=409, detail="subscription already exists")

    await run_db(_ensure_no_active, sessionmaker=SessionLocal)

    if settings.billing_provider is BillingProvider.DUMMY:
        checkout_id = f"dummy-{uuid4().hex}"

        def _create_sub(session: Session) -> None:
            sub = Subscription(
                user_id=user_id,
                plan=plan,
                status=cast(SubStatus, SubStatus.active.value),
                provider=settings.billing_provider.value,
                transaction_id=checkout_id,
                start_date=now,
                end_date=None,
            )
            session.add(sub)
            log_billing_event(
                session,
                user_id,
                BillingEvent.INIT,
                {"plan": plan.value},
            )
            log_billing_event(
                session,
                user_id,
                BillingEvent.CHECKOUT_CREATED,
                {"plan": plan.value, "checkout_id": checkout_id},
            )
            session.commit()

        await run_db(_create_sub, sessionmaker=SessionLocal)
        return DummyCheckoutSchema(checkout_id=checkout_id)

    checkout = await create_checkout(settings, plan.value)

    def _create_subscription(session: Session) -> None:
        sub = Subscription(
            user_id=user_id,
            plan=plan,
            status=cast(SubStatus, SubStatus.active.value),
            provider=settings.billing_provider.value,
            transaction_id=checkout["id"],
            start_date=now,
            end_date=None,
        )
        session.add(sub)
        log_billing_event(
            session,
            user_id,
            BillingEvent.INIT,
            {"plan": plan.value},
        )
        log_billing_event(
            session,
            user_id,
            BillingEvent.CHECKOUT_CREATED,
            {"plan": plan.value, "checkout_id": checkout["id"]},
        )
        session.commit()

    try:
        await run_db(_create_subscription, sessionmaker=SessionLocal)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409, detail="subscription already exists"
        ) from exc
    return CheckoutSchema.model_validate(checkout)


@router.post("/webhook")
async def webhook(
    request: Request,
    event: WebhookEvent,
    settings: BillingSettings = Depends(_require_billing_enabled),
) -> dict[str, str]:
    """Process provider webhook and activate subscription."""

    ip_header = request.headers.get("X-Forwarded-For")
    if ip_header is not None:
        ip = ip_header.split(",")[0].strip()
    elif request.client is not None:
        ip = request.client.host
    else:
        ip = ""
    if not await verify_webhook(settings, event, request.headers, ip):
        raise HTTPException(status_code=400, detail="invalid signature")

    now = datetime.now(timezone.utc)

    def _activate(session: Session) -> bool:
        stmt = select(Subscription).where(
            Subscription.transaction_id == event.transaction_id
        )
        sub = session.scalars(stmt).first()
        if sub is None:
            return False

        conflict_stmt = select(Subscription).where(
            Subscription.user_id == sub.user_id,
            Subscription.status == SubStatus.active.value,
            Subscription.end_date.is_not(None),
            Subscription.end_date > now,
            Subscription.id != sub.id,
        )
        conflict = session.scalars(conflict_stmt).first()
        if conflict is not None:
            logger.warning(
                "active subscription exists, expiring previous",
                extra={
                    "user_id": sub.user_id,
                    "transaction_id": event.transaction_id,
                    "conflict_transaction_id": conflict.transaction_id,
                },
            )
            conflict.status = cast(SubStatus, SubStatus.expired.value)
            conflict.end_date = now

        sub_end = sub.end_date
        if sub_end is not None and sub_end.tzinfo is None:
            sub_end = sub_end.replace(tzinfo=timezone.utc)
        if (
            sub.status == SubStatus.active.value
            and sub_end is not None
            and sub_end > now
        ):
            return False
        base = sub_end if sub_end is not None and sub_end > now else now
        sub.plan = event.plan
        sub.status = cast(SubStatus, SubStatus.active.value)
        sub.end_date = base + timedelta(days=30)
        log_billing_event(
            session,
            sub.user_id,
            BillingEvent.WEBHOOK_OK,
            {
                "transaction_id": event.transaction_id,
                "plan": event.plan,
            },
        )
        session.commit()
        return True

    updated = await run_db(_activate, sessionmaker=SessionLocal)
    status = "processed" if updated else "ignored"
    logger.info("webhook %s %s", event.transaction_id, status)
    return {"status": status}


@router.post("/mock-webhook/{checkout_id}")
async def mock_webhook(
    checkout_id: str,
    x_token: str | None = Header(default=None, alias="X-Admin-Token"),
    settings: BillingSettings = Depends(_require_billing_enabled),
) -> dict[str, str]:
    """Simulate provider webhook to activate a subscription in test mode."""

    if not settings.billing_test_mode:
        raise HTTPException(status_code=403, detail="test mode disabled")
    if settings.billing_admin_token is None or x_token != settings.billing_admin_token:
        raise HTTPException(status_code=403, detail="forbidden")

    def _activate(session: Session) -> bool:
        stmt = select(Subscription).where(Subscription.transaction_id == checkout_id)
        sub = session.scalars(stmt).first()
        if sub is None:
            return False
        end_date = datetime.now(timezone.utc) + timedelta(days=30)
        # keep existing plan, set status and end date only
        sub.status = cast(SubStatus, SubStatus.active.value)
        sub.end_date = end_date
        log_billing_event(
            session,
            sub.user_id,
            BillingEvent.WEBHOOK_OK,
            {"transaction_id": checkout_id},
        )
        session.commit()
        return True

    updated = await run_db(_activate, sessionmaker=SessionLocal)
    if not updated:
        raise HTTPException(status_code=404, detail="subscription not found")
    return {"status": "ok"}


@router.post("/admin/mock_webhook")
async def admin_mock_webhook(
    transaction_id: str,
    x_token: str | None = Header(default=None, alias="X-Admin-Token"),
    settings: BillingSettings = Depends(_require_billing_enabled),
) -> dict[str, str]:
    """Manually activate a subscription in test mode."""

    if not settings.billing_test_mode:
        raise HTTPException(status_code=403, detail="test mode disabled")
    if settings.billing_admin_token is None or x_token != settings.billing_admin_token:
        raise HTTPException(status_code=403, detail="forbidden")

    def _activate(session: Session) -> bool:
        stmt = select(Subscription).where(Subscription.transaction_id == transaction_id)
        sub = session.scalars(stmt).first()
        if sub is None:
            return False
        end_date = datetime.now(timezone.utc) + timedelta(days=30)
        # keep existing plan, set status and end date only
        sub.status = cast(SubStatus, SubStatus.active.value)
        sub.end_date = end_date
        log_billing_event(
            session,
            sub.user_id,
            BillingEvent.WEBHOOK_OK,
            {"transaction_id": transaction_id},
        )
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
        for status in (
            SubStatus.active.value,
            SubStatus.trial.value,
        ):
            stmt = (
                select(Subscription)
                .where(
                    Subscription.user_id == user_id,
                    Subscription.status == status,
                )
                .order_by(Subscription.start_date.desc())
                .limit(1)
            )
            sub = session.scalars(stmt).first()
            if sub is not None:
                return sub
        stmt = (
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.start_date.desc())
            .limit(1)
        )
        return session.scalars(stmt).first()

    subscription = await run_db(_get_subscription, sessionmaker=SessionLocal)
    flags = FeatureFlags(
        billingEnabled=settings.billing_enabled,
        paywallMode=settings.paywall_mode.value,
        testMode=settings.billing_test_mode,
    )
    if subscription is None:
        return BillingStatusResponse(featureFlags=flags, subscription=None)
    return BillingStatusResponse(
        featureFlags=flags,
        subscription=SubscriptionSchema.model_validate(
            subscription, from_attributes=True
        ),
    )
