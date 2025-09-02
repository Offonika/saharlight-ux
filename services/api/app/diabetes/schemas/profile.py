from enum import Enum
from pydantic import BaseModel, Field, AliasChoices, ConfigDict, model_validator


class CarbUnits(str, Enum):
    """Enumerates carbohydrate measurement units."""

    GRAMS = "g"
    XE = "xe"


class TherapyType(str, Enum):
    """Available therapy types for a patient profile."""

    INSULIN = "insulin"
    TABLETS = "tablets"
    NONE = "none"
    MIXED = "mixed"


class RapidInsulinType(str, Enum):
    """Types of rapid-acting insulin."""

    ASPART = "aspart"
    LISPRO = "lispro"
    GLULISINE = "glulisine"
    REGULAR = "regular"


class ProfileSettingsIn(BaseModel):
    """Incoming user settings for profile configuration."""

    timezone: str | None = None
    timezoneAuto: bool | None = Field(
        default=None,
        alias="timezoneAuto",
        validation_alias=AliasChoices("timezoneAuto", "timezone_auto"),
    )
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
    sosContact: str | None = Field(
        default=None,
        alias="sosContact",
        validation_alias=AliasChoices("sosContact", "sos_contact"),
    )
    sosAlertsEnabled: bool | None = Field(
        default=None,
        alias="sosAlertsEnabled",
        validation_alias=AliasChoices("sosAlertsEnabled", "sos_alerts_enabled"),
    )
    therapyType: TherapyType | None = Field(
        default=None,
        alias="therapyType",
        validation_alias=AliasChoices("therapyType", "therapy_type"),
    )
    rapidInsulinType: RapidInsulinType | None = Field(
        default=None,
        alias="rapidInsulinType",
        validation_alias=AliasChoices("rapidInsulinType", "insulin_type"),
    )
    maxBolus: float | None = Field(
        default=None,
        alias="maxBolus",
        validation_alias=AliasChoices("maxBolus", "max_bolus"),
    )
    preBolus: int | None = Field(
        default=None,
        alias="preBolus",
        validation_alias=AliasChoices("preBolus", "prebolus_min"),
    )
    afterMealMinutes: int | None = Field(
        default=None,
        alias="afterMealMinutes",
        validation_alias=AliasChoices(
            "afterMealMinutes",
            "postmeal_check_min",
            "postMealCheckMin",
            "defaultAfterMealMinutes",
        ),
    )

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def _validate_values(self) -> "ProfileSettingsIn":
        if self.dia is not None and not (1 <= self.dia <= 24):
            raise ValueError("dia must be between 1 and 24 hours")
        if self.roundStep is not None and self.roundStep <= 0:
            raise ValueError("roundStep must be positive")
        if self.maxBolus is not None and self.maxBolus <= 0:
            raise ValueError("maxBolus must be positive")
        if self.preBolus is not None and not (0 <= self.preBolus <= 60):
            raise ValueError("preBolus must be between 0 and 60 minutes")
        if self.afterMealMinutes is not None and not (0 <= self.afterMealMinutes <= 240):
            raise ValueError("afterMealMinutes must be between 0 and 240 minutes")
        return self


class ProfileSettingsOut(ProfileSettingsIn):
    """Outgoing user settings with required fields."""

    timezone: str
    timezoneAuto: bool = Field(alias="timezoneAuto")
    dia: float
    roundStep: float = Field(alias="roundStep")
    carbUnits: CarbUnits = Field(alias="carbUnits")
    sosContact: str | None = Field(default=None, alias="sosContact")
    sosAlertsEnabled: bool = Field(alias="sosAlertsEnabled")
    therapyType: TherapyType = Field(alias="therapyType")
    rapidInsulinType: RapidInsulinType | None = Field(default=None, alias="rapidInsulinType")
    maxBolus: float = Field(alias="maxBolus")
    preBolus: int = Field(alias="preBolus")
    afterMealMinutes: int = Field(alias="afterMealMinutes")
