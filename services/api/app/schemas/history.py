from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional, cast, get_args

from pydantic import BaseModel, Field, field_validator


HistoryType = Literal["measurement", "meal", "insulin"]

ALLOWED_HISTORY_TYPES: set[HistoryType] = cast(
    set[HistoryType], set(get_args(HistoryType))
)


class HistoryRecordSchema(BaseModel):
    """Schema for user history records."""

    id: str
    date: date
    time: str = Field(pattern=r"^\d{2}:\d{2}$")
    sugar: Optional[float] = None
    carbs: Optional[float] = None
    breadUnits: Optional[float] = None
    insulin: Optional[float] = None
    notes: Optional[str] = None
    type: HistoryType

    @field_validator("time")
    @classmethod
    def validate_time(cls, value: str) -> str:
        try:
            datetime.strptime(value, "%H:%M")
        except ValueError as exc:  # pragma: no cover - pydantic handles messaging
            raise ValueError("time must be in HH:MM format") from exc
        return value
