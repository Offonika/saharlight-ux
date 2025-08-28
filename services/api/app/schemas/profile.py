from __future__ import annotations

from typing import Optional
from datetime import time

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


class ProfileSchema(BaseModel):
    telegramId: int = Field(
        alias="telegramId", validation_alias=AliasChoices("telegramId", "telegram_id")
    )
    icr: Optional[float] = None
    cf: Optional[float] = None
    target: Optional[float] = None
    low: Optional[float] = None
    high: Optional[float] = None
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

    @model_validator(mode="after")
    def compute_target(self) -> "ProfileSchema":
        if self.target is None and self.low is not None and self.high is not None:
            self.target = (self.low + self.high) / 2
        return self
