from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Message:
    """Minimal Telegram Message stub for tests."""

    text: str = ""
    texts: List[str] = field(default_factory=list)
    markups: List[Any] = field(default_factory=list)
    kwargs: List[Dict[str, Any]] = field(default_factory=list)

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.markups.append(kwargs.get("reply_markup"))
        self.kwargs.append(kwargs)

    async def delete(self) -> None:  # pragma: no cover - behavior not needed
        """Stub delete method."""
        return None


@dataclass
class User:
    """Minimal User stub."""

    id: int


@dataclass
class Update:
    """Minimal Update stub that allows dynamic attributes."""

    message: Message | None = None
    effective_user: User | None = None


@dataclass
class CallbackContext:
    """Minimal CallbackContext stub."""

    args: List[str] | None = None
    user_data: Dict[str, Any] = field(default_factory=dict)
    chat_data: Dict[str, Any] = field(default_factory=dict)
