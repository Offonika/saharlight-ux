from __future__ import annotations

from typing import NotRequired, TypedDict


class UserContext(TypedDict):
    """Telegram user data supplied via WebApp init data."""

    id: int
    first_name: NotRequired[str]
    last_name: NotRequired[str]
    username: NotRequired[str]
    language_code: NotRequired[str]
    is_premium: NotRequired[bool]
    age_group: NotRequired[str | None]
    learning_level: NotRequired[str | None]
    diabetes_type: NotRequired[str | None]
