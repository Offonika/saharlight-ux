from __future__ import annotations

from collections.abc import Mapping

# Mapping of topic slug to human readable Russian title
TOPICS_RU: dict[str, str] = {
    "xe_basics": "Хлебные единицы",
    "healthy-eating": "Здоровое питание",
    "basics-of-diabetes": "Основы диабета",
    "insulin-usage": "Инсулин",
}


async def choose_initial_topic(profile: Mapping[str, str | None]) -> str:
    """Return an initial topic slug for the user profile.

    Currently selects the first available topic; more complex logic can be
    implemented later based on *profile*.
    """

    return next(iter(TOPICS_RU))


__all__ = ["TOPICS_RU", "choose_initial_topic"]
