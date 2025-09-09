from __future__ import annotations

from typing import cast

__all__ = ["get_learning_profile"]


async def get_learning_profile(user_id: int) -> dict[str, str | None]:
    """Return stored learning profile overrides for ``user_id``.

    The default implementation returns an empty mapping and is intended to be
    patched in tests or extended with real database logic.
    """
    return cast(dict[str, str | None], {})
