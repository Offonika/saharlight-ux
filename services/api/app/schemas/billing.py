from __future__ import annotations

from datetime import datetime
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from services.api.app.diabetes.services.db import SubscriptionPlan, SubStatus


class FeatureFlags(BaseModel):
    """Flags describing billing-related features."""

    billingEnabled: bool = Field(alias="billingEnabled")
    paywallMode: str = Field(alias="paywallMode")
    testMode: bool = Field(alias="testMode")

    model_config = ConfigDict(populate_by_name=True)


class CheckoutSchema(BaseModel):
    """Checkout information returned by billing provider."""

    id: str
    url: str


class WebhookEvent(BaseModel):
    """Webhook event payload from billing provider."""

    event_id: str = Field(alias="event_id")
    transaction_id: str = Field(alias="transaction_id")
    plan: SubscriptionPlan
    signature: str

    model_config = ConfigDict(populate_by_name=True)


class SubscriptionSchema(BaseModel):
    """Information about a user subscription."""

    plan: SubscriptionPlan
    status: SubStatus
    provider: str
    startDate: datetime = Field(
        alias="startDate", validation_alias=AliasChoices("startDate", "start_date")
    )
    endDate: datetime | None = Field(
        default=None,
        alias="endDate",
        validation_alias=AliasChoices("endDate", "end_date"),
    )

    model_config = ConfigDict(
        populate_by_name=True, from_attributes=True, use_enum_values=True
    )

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status(cls, value: str | SubStatus) -> str | SubStatus:
        """Allow case-insensitive status values from billing API."""
        if isinstance(value, str):
            return value.lower()
        return value


class BillingStatusResponse(BaseModel):
    """Response schema for billing status requests."""

    featureFlags: FeatureFlags = Field(alias="featureFlags")
    subscription: SubscriptionSchema | None

    model_config = ConfigDict(populate_by_name=True)
