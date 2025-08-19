"""Handlers package public exports and shared types."""

from typing import TypedDict

from telegram import CallbackQuery


class UserData(TypedDict, total=False):
    """Mutable mapping used to store per-user state in handlers."""

    awaiting_report_date: bool
    thread_id: str
    pending_entry: dict[str, object]
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
    __file_path: str
    reminder_id: int
    chat_id: int


from .dose_calc import _cancel_then  # noqa: E402

__all__ = ["_cancel_then", "UserData"]

