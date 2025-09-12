from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AssistantMenu:
    """Texts for assistant-related buttons."""

    assistant: str
    learn: str
    chat: str
    labs: str
    visit: str


def render_assistant_menu(emoji: bool) -> AssistantMenu:
    """Return assistant menu button texts.

    Args:
        emoji: Whether to include emoji in button labels.
    """

    if emoji:
        return AssistantMenu(
            assistant="🤖 Ассистент_AI",
            learn="🎓 Обучение",
            chat="💬 Чат",
            labs="🧪 Анализы",
            visit="🩺 Визит",
        )
    return AssistantMenu(
        assistant="Ассистент_AI",
        learn="Обучение",
        chat="Чат",
        labs="Анализы",
        visit="Визит",
    )


__all__ = ["AssistantMenu", "render_assistant_menu"]
