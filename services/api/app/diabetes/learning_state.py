from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import MutableMapping

KEY = "learn_state"


@dataclass
class LearnState:
    """Ephemeral lesson state stored in ``context.user_data``."""

    topic: str
    step: int
    last_step_text: str | None = None
    prev_summary: str | None = None
    awaiting: bool = True


def get_state(data: MutableMapping[str, object]) -> LearnState | None:
    """Return ``LearnState`` from ``data`` if present."""

    raw = data.get(KEY)
    if isinstance(raw, dict):
        try:
            return LearnState(**raw)
        except TypeError:
            return None
    return None


def set_state(data: MutableMapping[str, object], state: LearnState) -> None:
    """Store ``state`` in ``data``."""

    data[KEY] = asdict(state)


def clear_state(data: MutableMapping[str, object]) -> None:
    """Remove lesson state from ``data`` if it exists."""

    data.pop(KEY, None)
