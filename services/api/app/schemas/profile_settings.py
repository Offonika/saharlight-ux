from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProfileSettings(BaseModel):
    grams_per_xe: int = Field(alias="gramsPerXe")
    round_step: float = Field(alias="roundStep")
    max_bolus: float = Field(alias="maxBolus")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def validate_values(self) -> "ProfileSettings":
        if self.grams_per_xe not in (10, 12):
            raise ValueError("grams_per_xe must be 10 or 12")
        if self.round_step not in (0.5, 1.0):
            raise ValueError("round_step must be 0.5 or 1.0")
        if not (0.5 <= self.max_bolus <= 25.0):
            raise ValueError("max_bolus out of range")
        return self


class ProfileSettingsPatch(BaseModel):
    grams_per_xe: int | None = Field(default=None, alias="gramsPerXe")
    round_step: float | None = Field(default=None, alias="roundStep")
    max_bolus: float | None = Field(default=None, alias="maxBolus")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def validate_values(self) -> "ProfileSettingsPatch":
        if self.grams_per_xe is not None and self.grams_per_xe not in (10, 12):
            raise ValueError("grams_per_xe must be 10 or 12")
        if self.round_step is not None and self.round_step not in (0.5, 1.0):
            raise ValueError("round_step must be 0.5 or 1.0")
        if self.max_bolus is not None and not (0.5 <= self.max_bolus <= 25.0):
            raise ValueError("max_bolus out of range")
        return self
