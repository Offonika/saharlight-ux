from __future__ import annotations

from services.api.app.assistant.models import LessonLog


async def add_lesson_log(*args: object, **kwargs: object) -> None:
    """Stub for backward compatibility."""
    return None


def get_lesson_logs(*args: object, **kwargs: object) -> list[LessonLog]:
    """Stub for backward compatibility."""
    return []


__all__ = ["add_lesson_log", "get_lesson_logs"]
