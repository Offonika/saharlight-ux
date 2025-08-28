from __future__ import annotations

from typing import Any, Optional
from datetime import time

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


class ProfileSchema(BaseModel):
    telegramId: int = Field(
        alias="telegramId", validation_alias=AliasChoices("telegramId", "telegram_id")
    )
    icr: float = Field(validation_alias=AliasChoices("icr", "cf"))
    cf: float
    target: Optional[float] = None
    low: float = Field(validation_alias=AliasChoices("low", "targetLow"))
    high: float = Field(validation_alias=AliasChoices("high", "targetHigh"))
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
    orgId: Optional[int] = None
    sosContact: Optional[str] = Field(
        default=None,
        alias="sosContact",
        validation_alias=AliasChoices("sosContact", "sos_contact"),
    )
    sosAlertsEnabled: bool = Field(
        default=True,
        alias="sosAlertsEnabled",
        validation_alias=AliasChoices("sosAlertsEnabled", "sos_alerts_enabled"),
    )

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def _check_aliases(cls, data: dict[str, Any]) -> dict[str, Any]:
        pairs = {
            "low": "targetLow",
            "high": "targetHigh",
        }
        for field, alias in pairs.items():
            if field in data and alias in data:
                if data[field] != data[alias]:
                    raise ValueError(f"{field} mismatch")
            elif alias in data and field not in data:
                data[field] = data[alias]

        if "icr" not in data and "cf" in data:
            data["icr"] = data["cf"]

        return data

    @model_validator(mode="after")
    def _compute_target(self) -> "ProfileSchema":
        if self.low >= self.high:
            raise ValueError("low must be less than high")
        if self.target is None:
            self.target = (self.low + self.high) / 2
        return self
