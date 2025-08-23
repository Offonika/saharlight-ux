from __future__ import annotations

from datetime import time as time_
from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ReminderSchema(BaseModel):
    telegramId: int = Field(alias="telegramId", validation_alias=AliasChoices("telegramId", "telegram_id"))
    id: Optional[int] = None
    type: str
    title: Optional[str] = None
    time: Optional[time_] = None
    intervalHours: Optional[int] = None
    minutesAfter: Optional[int] = None
    isEnabled: bool = True
    orgId: Optional[int] = None

    model_config = ConfigDict(populate_by_name=True)
