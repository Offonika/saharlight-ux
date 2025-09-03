"""Handlers package public exports and shared types."""

import datetime
from typing import TypedDict

from telegram import CallbackQuery


class EntryData(TypedDict, total=False):
    """Data used to create or update an :class:`Entry`."""

    telegram_id: int
    event_time: datetime.datetime
    xe: float | None
    carbs_g: float | None
    dose: float | None
    sugar_before: float | None
    photo_bytes: bytes | None


class UserData(TypedDict, total=False):
    """Mutable mapping used to store per-user state in handlers."""

    awaiting_report_date: bool
    thread_id: str
    pending_entry: EntryData
    pending_fields: list[str]
    dose_method: str
    edit_id: int | None
    edit_entry: dict[str, object]
    edit_field: str
    edit_query: CallbackQuery | None
    profile_icr: float
    profile_cf: float
    profile_target: float
    profile_low: float
    reminder_id: int
    chat_id: int


from .dose_calc import _cancel_then  # noqa: E402

__all__ = ["_cancel_then", "EntryData", "UserData"]

