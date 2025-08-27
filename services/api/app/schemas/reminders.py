from __future__ import annotations

from datetime import datetime as datetime_, time as time_
from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


class ReminderSchema(BaseModel):
    telegramId: int = Field(alias="telegramId", validation_alias=AliasChoices("telegramId", "telegram_id"))
    id: Optional[int] = None
    type: str
    title: Optional[str] = None
    time: Optional[time_] = None
    intervalMinutes: Optional[int] = Field(
        default=None,
        alias="intervalMinutes",
        validation_alias=AliasChoices("intervalMinutes", "interval_minutes"),
    )
    minutesAfter: Optional[int] = Field(
        default=None,
        alias="minutesAfter",
        validation_alias=AliasChoices("minutesAfter", "minutes_after"),
    )
    intervalHours: Optional[int] = Field(
        default=None,
        alias="intervalHours",
        validation_alias=AliasChoices("intervalHours", "interval_hours"),
    )
    isEnabled: bool = True
    orgId: Optional[int] = None
    lastFiredAt: Optional[datetime_] = Field(
        default=None,
        alias="lastFiredAt",
        validation_alias=AliasChoices("lastFiredAt", "last_fired_at"),
    )
    fires7d: int = Field(default=0, alias="fires7d")

    @model_validator(mode="after")
    def _normalize(self) -> "ReminderSchema":
        if self.intervalHours is not None and self.intervalMinutes is None:
            self.intervalMinutes = self.intervalHours * 60
        return self

    model_config = ConfigDict(populate_by_name=True)
