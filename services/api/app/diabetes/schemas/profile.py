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

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def _validate_values(self) -> "ProfileSettingsIn":
        if self.dia is not None and not (1 <= self.dia <= 24):
            raise ValueError("dia must be between 1 and 24 hours")
        if self.roundStep is not None and self.roundStep <= 0:
            raise ValueError("roundStep must be positive")
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
