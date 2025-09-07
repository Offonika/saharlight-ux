from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast


def make_update(**kwargs: Any) -> object:
    """Create update stub with mandatory effective_user."""
    return cast(object, SimpleNamespace(effective_user=SimpleNamespace(id=1), **kwargs))


def make_context(
    *, user_data: dict[str, object] | None = None, **kwargs: Any
) -> object:
    """Create context stub with mandatory bot_data."""
    return SimpleNamespace(
        user_data=user_data if user_data is not None else {},
        bot_data={},
        **kwargs,
    )
