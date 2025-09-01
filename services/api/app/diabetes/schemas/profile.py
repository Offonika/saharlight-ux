from enum import Enum
from pydantic import BaseModel, Field, AliasChoices, ConfigDict, model_validator


class CarbUnits(str, Enum):
    """Enumerates carbohydrate measurement units."""

    GRAMS = "g"
    XE = "xe"


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

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def _validate_values(self) -> "ProfileSettingsIn":
        if self.dia is not None and not (1 <= self.dia <= 24):
            raise ValueError("dia must be between 1 and 24 hours")
        if self.roundStep is not None and self.roundStep not in (0.5, 1.0):
            raise ValueError("roundStep must be one of 0.5 or 1.0")
        if self.gramsPerXe is not None and self.gramsPerXe not in (10, 12):
            raise ValueError("gramsPerXe must be 10 or 12")
        return self


class ProfileSettingsOut(ProfileSettingsIn):
    """Outgoing user settings with required fields."""

    timezone: str
    timezoneAuto: bool = Field(alias="timezoneAuto")
    dia: float
    roundStep: float = Field(alias="roundStep")
    carbUnits: CarbUnits = Field(alias="carbUnits")
    gramsPerXe: float = Field(alias="gramsPerXe")
