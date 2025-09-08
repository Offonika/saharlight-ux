"""Handlers package public exports and shared types."""

import datetime

try:
    from typing import TypedDict  # Python 3.12+
except ImportError:  # Python <3.12
    from typing_extensions import TypedDict


class EntryData(TypedDict, total=False):
    """Data used to create or update an :class:`Entry`."""

    telegram_id: int
    event_time: datetime.datetime
    xe: float | None
    carbs_g: float | None
    weight_g: float | None
    protein_g: float | None
    fat_g: float | None
    calories_kcal: float | None
    dose: float | None
    sugar_before: float | None
    photo_path: str | None


class EditMessageMeta(TypedDict):
    """Metadata about the message being edited."""

    chat_id: int
    message_id: int


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
    edit_query: EditMessageMeta
    profile_icr: float
    profile_cf: float
    profile_target: float
    profile_low: float
    __file_path: str
    reminder_id: int
    chat_id: int


from .dose_calc import _cancel_then  # noqa: E402

__all__ = ["_cancel_then", "EntryData", "EditMessageMeta", "UserData"]
