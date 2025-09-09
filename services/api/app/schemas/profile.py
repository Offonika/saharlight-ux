from __future__ import annotations

from typing import Optional
from datetime import time

from fastapi import HTTPException
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

from ..diabetes.schemas.profile import (
    CarbUnits,
    GlucoseUnits,
    RapidInsulinType,
    TherapyType,
)


class _ProfileBase(BaseModel):
    telegramId: int = Field(
        alias="telegramId", validation_alias=AliasChoices("telegramId", "telegram_id")
    )
    icr: Optional[float] = Field(
        default=None,
        alias="icr",
        validation_alias=AliasChoices("icr"),
    )
    cf: Optional[float] = Field(
        default=None,
        alias="cf",
        validation_alias=AliasChoices("cf"),
    )
    target: Optional[float] = None
    low: Optional[float] = Field(
        default=None,
        alias="low",
        validation_alias=AliasChoices("low", "targetLow"),
    )
    high: Optional[float] = Field(
        default=None,
        alias="high",
        validation_alias=AliasChoices("high", "targetHigh"),
    )
    orgId: Optional[int] = None
    sosContact: Optional[str] = Field(
        default=None,
        alias="sosContact",
        validation_alias=AliasChoices("sosContact", "sos_contact"),
    )
    therapyType: TherapyType | None = Field(
        default=None,
        alias="therapyType",
        validation_alias=AliasChoices("therapyType", "therapy_type"),
    )

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="before")
    def alias_mismatch(cls, values: dict[str, object]) -> dict[str, object]:
        def _check(a: str, b: str, name: str) -> None:
            if a in values and b in values and values[a] != values[b]:
                raise HTTPException(status_code=422, detail=f"{name} mismatch")

        _check("low", "targetLow", "low")
        _check("high", "targetHigh", "high")
        return values

    @model_validator(mode="after")
    def compute_target(self) -> "_ProfileBase":
        if self.low is not None and self.high is not None:
            if self.target is None:
                self.target = (self.low + self.high) / 2
        return self


class ProfileSchema(_ProfileBase):
    quietStart: time = Field(
        default=time(23, 0),
        alias="quietStart",
        validation_alias=AliasChoices("quietStart", "quiet_start"),
    )
    quietEnd: time = Field(
        default=time(7, 0),
        alias="quietEnd",
        validation_alias=AliasChoices("quietEnd", "quiet_end"),
    )
    sosAlertsEnabled: bool = Field(
        default=True,
        alias="sosAlertsEnabled",
        validation_alias=AliasChoices("sosAlertsEnabled", "sos_alerts_enabled"),
    )
    timezone: str = Field(
        default="UTC",
        alias="timezone",
        validation_alias=AliasChoices("timezone"),
    )
    timezoneAuto: bool = Field(
        default=True,
        alias="timezoneAuto",
        validation_alias=AliasChoices("timezoneAuto", "timezone_auto"),
    )
    dia: float = 4.0
    roundStep: float = Field(
        default=0.5,
        alias="roundStep",
        validation_alias=AliasChoices("roundStep", "round_step"),
    )
    carbUnits: CarbUnits = Field(
        default=CarbUnits.GRAMS,
        alias="carbUnits",
        validation_alias=AliasChoices("carbUnits", "carb_units"),
    )
    gramsPerXe: float = Field(
        default=12.0,
        alias="gramsPerXe",
        validation_alias=AliasChoices("gramsPerXe", "grams_per_xe"),
    )
    glucoseUnits: GlucoseUnits = Field(
        default=GlucoseUnits.MMOL_L,
        alias="glucoseUnits",
        validation_alias=AliasChoices("glucoseUnits", "glucose_units"),
    )
    rapidInsulinType: RapidInsulinType | None = Field(
        default=None,
        alias="rapidInsulinType",
        validation_alias=AliasChoices("rapidInsulinType", "rapid_insulin_type"),
    )
    maxBolus: float = Field(
        default=10.0,
        alias="maxBolus",
        validation_alias=AliasChoices("maxBolus", "max_bolus"),
    )
    preBolus: int = Field(
        default=0,
        alias="preBolus",
        validation_alias=AliasChoices("preBolus", "pre_bolus", "prebolus_min"),
    )
    afterMealMinutes: int = Field(
        default=0,
        alias="afterMealMinutes",
        validation_alias=AliasChoices(
            "afterMealMinutes",
            "after_meal_minutes",
            "postMealCheckMin",
            "postmeal_check_min",
        ),
    )


class ProfileUpdateSchema(_ProfileBase):
    quietStart: time | None = Field(
        default=None,
        alias="quietStart",
        validation_alias=AliasChoices("quietStart", "quiet_start"),
    )
    quietEnd: time | None = Field(
        default=None,
        alias="quietEnd",
        validation_alias=AliasChoices("quietEnd", "quiet_end"),
    )
    sosAlertsEnabled: bool | None = Field(
        default=None,
        alias="sosAlertsEnabled",
        validation_alias=AliasChoices("sosAlertsEnabled", "sos_alerts_enabled"),
    )
    timezone: str | None = Field(
        default=None,
        alias="timezone",
        validation_alias=AliasChoices("timezone"),
    )
    timezoneAuto: bool | None = Field(
        default=None,
        alias="timezoneAuto",
        validation_alias=AliasChoices("timezoneAuto", "timezone_auto"),
    )


class ProfilePatchSchema(ProfileUpdateSchema):
    """Profile update payload including extended settings."""

    dia: float | None = None
    roundStep: float | None = Field(
        default=None,
        alias="roundStep",
        validation_alias=AliasChoices("roundStep", "round_step"),
    )
    carbUnits: CarbUnits | None = Field(
        default=None,
        alias="carbUnits",
        validation_alias=AliasChoices("carbUnits", "carb_units"),
    )
    gramsPerXe: float | None = Field(
        default=None,
        alias="gramsPerXe",
        validation_alias=AliasChoices("gramsPerXe", "grams_per_xe"),
    )
    glucoseUnits: GlucoseUnits | None = Field(
        default=None,
        alias="glucoseUnits",
        validation_alias=AliasChoices("glucoseUnits", "glucose_units"),
    )
    rapidInsulinType: RapidInsulinType | None = Field(
        default=None,
        alias="rapidInsulinType",
        validation_alias=AliasChoices("rapidInsulinType", "rapid_insulin_type"),
    )
    maxBolus: float | None = Field(
        default=None,
        alias="maxBolus",
        validation_alias=AliasChoices("maxBolus", "max_bolus"),
    )
    preBolus: int | None = Field(
        default=None,
        alias="preBolus",
        validation_alias=AliasChoices("preBolus", "pre_bolus", "prebolus_min"),
    )
    afterMealMinutes: int | None = Field(
        default=None,
        alias="afterMealMinutes",
        validation_alias=AliasChoices(
            "afterMealMinutes",
            "after_meal_minutes",
            "postMealCheckMin",
            "postmeal_check_min",
        ),
    )

    model_config = ConfigDict(populate_by_name=True)
