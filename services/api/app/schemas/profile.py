from __future__ import annotations

from typing import Optional
from datetime import time

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

class ProfileSchema(BaseModel):
    telegramId: int = Field(alias="telegramId", validation_alias=AliasChoices("telegramId", "telegram_id"))
    icr: float
    cf: float
    target: float
    low: float
    high: float
    quietStart: str = Field(
        default="23:00",
        alias="quietStart",
        validation_alias=AliasChoices("quietStart", "quiet_start"),
    )
    quietEnd: str = Field(
        default="07:00",
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
        validation_alias=AliasChoices(
            "sosAlertsEnabled", "sos_alerts_enabled"
        ),
    )
    quietStart: time = Field(
        default=time(22, 0),
        alias="quietStart",
        validation_alias=AliasChoices("quietStart", "quiet_start"),
    )
    quietEnd: time = Field(
        default=time(7, 0),
        alias="quietEnd",
        validation_alias=AliasChoices("quietEnd", "quiet_end"),
    )

    model_config = ConfigDict(populate_by_name=True)
