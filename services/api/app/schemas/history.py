from __future__ import annotations

from datetime import date, time
from typing import Literal, Optional, cast, get_args

from pydantic import BaseModel, field_serializer


HistoryType = Literal["measurement", "meal", "insulin"]

ALLOWED_HISTORY_TYPES: set[HistoryType] = cast(set[HistoryType], set(get_args(HistoryType)))


class HistoryRecordSchema(BaseModel):
    """Schema for user history records."""

    id: str
    date: date
    time: time
    sugar: Optional[float] = None
    carbs: Optional[float] = None
    breadUnits: Optional[float] = None
    insulin: Optional[float] = None
    notes: Optional[str] = None
    type: HistoryType

    @field_serializer("date")
    def _serialize_date(self, value: date) -> str:
        return value.isoformat()

    @field_serializer("time")
    def _serialize_time(self, value: time) -> str:
        return value.strftime("%H:%M")
