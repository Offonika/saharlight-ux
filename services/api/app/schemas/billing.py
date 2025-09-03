from __future__ import annotations

from datetime import datetime
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from services.api.app.diabetes.services.db import SubscriptionPlan, SubscriptionStatus


class FeatureFlags(BaseModel):
    """Flags describing billing-related features."""

    billingEnabled: bool = Field(alias="billingEnabled")
    paywallMode: str = Field(alias="paywallMode")

    model_config = ConfigDict(populate_by_name=True)


class SubscriptionSchema(BaseModel):
    """Information about a user subscription."""

    plan: SubscriptionPlan
    status: SubscriptionStatus
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


class BillingStatusResponse(BaseModel):
    """Response schema for billing status requests."""

    featureFlags: FeatureFlags = Field(alias="featureFlags")
    subscription: SubscriptionSchema | None

    model_config = ConfigDict(populate_by_name=True)
