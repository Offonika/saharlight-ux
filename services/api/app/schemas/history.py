from __future__ import annotations

from typing import Literal, Optional, cast, get_args

from pydantic import BaseModel


HistoryType = Literal["measurement", "meal", "insulin"]

ALLOWED_HISTORY_TYPES: set[HistoryType] = cast(
    set[HistoryType], set(get_args(HistoryType))
)


class HistoryRecordSchema(BaseModel):
    """Schema for user history records."""

    id: str
    date: str
    time: str
    sugar: Optional[float] = None
    carbs: Optional[float] = None
    breadUnits: Optional[float] = None
    insulin: Optional[float] = None
    notes: Optional[str] = None
    type: HistoryType
