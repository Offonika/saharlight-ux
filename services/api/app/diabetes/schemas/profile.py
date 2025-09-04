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
    """Enumerates rapid insulin types."""

    ASPART = "aspart"
    LISPRO = "lispro"
    GLULISINE = "glulisine"
    REGULAR = "regular"


class GlucoseUnits(str, Enum):
    """Available blood glucose measurement units."""

    MMOL_L = "mmol/L"
    MG_DL = "mg/dL"


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

    @model_validator(mode="after")
    def _validate_values(self) -> "ProfileSettingsIn":
        if self.dia is not None and not (1 <= self.dia <= 24):
            raise ValueError("dia must be between 1 and 24 hours")
        if self.roundStep is not None and self.roundStep <= 0:
            raise ValueError("roundStep must be positive")
        if self.gramsPerXe is not None and self.gramsPerXe <= 0:
            raise ValueError("gramsPerXe must be positive")
        if self.maxBolus is not None and self.maxBolus <= 0:
            raise ValueError("maxBolus must be positive")
        if self.preBolus is not None and not (0 <= self.preBolus <= 60):
            raise ValueError("preBolus must be between 0 and 60")
        if self.afterMealMinutes is not None and not (0 <= self.afterMealMinutes <= 240):
            raise ValueError("afterMealMinutes must be between 0 and 240")
        return self


class ProfileSettingsOut(ProfileSettingsIn):
    """Outgoing user settings with required fields."""

    timezone: str
    timezoneAuto: bool = Field(alias="timezoneAuto")
    dia: float
    roundStep: float = Field(alias="roundStep")
    carbUnits: CarbUnits = Field(alias="carbUnits")
    gramsPerXe: float = Field(alias="gramsPerXe")
    glucoseUnits: GlucoseUnits = Field(alias="glucoseUnits")
    sosContact: str | None = Field(default=None, alias="sosContact")
    sosAlertsEnabled: bool = Field(alias="sosAlertsEnabled")
    therapyType: TherapyType = Field(alias="therapyType")
    rapidInsulinType: RapidInsulinType | None = Field(
        default=None, alias="rapidInsulinType"
    )
    maxBolus: float = Field(alias="maxBolus")
    preBolus: int = Field(alias="preBolus")
    afterMealMinutes: int = Field(alias="afterMealMinutes")
