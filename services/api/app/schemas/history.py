from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional, cast, get_args

from pydantic import BaseModel, Field, field_validator


HistoryType = Literal["measurement", "meal", "insulin"]

ALLOWED_HISTORY_TYPES: set[HistoryType] = cast(
    set[HistoryType], set(get_args(HistoryType))
)


class HistoryRecordSchema(BaseModel):
    """Public API schema for :class:`~services.api.app.diabetes.services.db.HistoryRecord`.

    The web application uses this lightweight structure to display a user's
    history of measurements, meals and insulin doses. It intentionally mirrors
    only a subset of the fields stored in :class:`Entry` and omits Telegram
    specific metadata such as photos or macronutrients.
    """

    id: str
    date: date
    time: str = Field(pattern=r"^\d{2}:\d{2}$")
    sugar: Optional[float] = Field(
        default=None, description="Blood glucose level before the event"
    )
    carbs: Optional[float] = Field(
        default=None, description="Consumed carbohydrates in grams"
    )
    breadUnits: Optional[float] = Field(
        default=None, description="Carbohydrates converted to bread units (XE)"
    )
    insulin: Optional[float] = Field(
        default=None, description="Injected insulin dose in units"
    )
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
