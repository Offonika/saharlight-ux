from __future__ import annotations

from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ReminderType(str, Enum):
    sugar = "sugar"
    insulin_short = "insulin_short"
    insulin_long = "insulin_long"
    after_meal = "after_meal"
    meal = "meal"
    sensor_change = "sensor_change"
    injection_site = "injection_site"
    custom = "custom"


class ScheduleKind(str, Enum):
    at_time = "at_time"
    every = "every"
    after_event = "after_event"


DayOfWeek = Literal[1, 2, 3, 4, 5, 6, 7]


class ReminderIn(BaseModel):
    telegramId: int = Field(alias="telegramId")
    id: Optional[int] = None
    type: ReminderType
    title: Optional[str] = None

    kind: ScheduleKind = ScheduleKind.at_time
    time: Optional[str] = None
    intervalMinutes: Optional[int] = None
    minutesAfter: Optional[int] = None

    # back-compat
    intervalHours: Optional[int] = None

    daysOfWeek: Optional[List[DayOfWeek]] = None
    isEnabled: bool = True
    orgId: Optional[int] = None

    @field_validator("time")
    @classmethod
    def _hhmm(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        import re

        if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", v):
            raise ValueError("time must be HH:MM")
        return v

    @model_validator(mode="after")
    def _normalize(self) -> "ReminderIn":
        if self.intervalHours and not self.intervalMinutes:
            self.intervalMinutes = self.intervalHours * 60

        provided = [
            bool(self.time),
            bool(self.intervalMinutes),
            bool(self.minutesAfter),
        ]
        if sum(provided) != 1:
            raise ValueError(
                "exactly one of time, intervalMinutes or minutesAfter must be provided"
            )

        if self.kind == ScheduleKind.at_time and not self.time:
            raise ValueError("kind=at_time requires time")
        if self.kind == ScheduleKind.every and not self.intervalMinutes:
            raise ValueError("kind=every requires intervalMinutes")
        if self.kind == ScheduleKind.after_event and not self.minutesAfter:
            raise ValueError("kind=after_event requires minutesAfter")
        return self


class ReminderOut(ReminderIn):
    nextAt: Optional[str] = None  # ISO datetime, filled by service
