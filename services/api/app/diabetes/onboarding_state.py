from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import cast

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

RESET_AFTER = timedelta(days=14)


@dataclass
class State:
    step: int = 0
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class OnboardingStateStore:
    """In-memory store for onboarding progress."""

    def __init__(self) -> None:
        self._states: dict[int, State] = {}

    def get(self, user_id: int) -> State:
        state = self._states.get(user_id)
        now = datetime.now(UTC)
        if state is None or now - state.updated_at > RESET_AFTER:
            state = State()
            self._states[user_id] = state
        return state

    def set_step(self, user_id: int, step: int) -> None:
        self._states[user_id] = State(step=step)

    def reset(self, user_id: int) -> None:
        self._states.pop(user_id, None)

    def to_dict(self) -> dict[int, dict[str, float | int]]:
        return {
            uid: {"step": s.step, "updated_at": s.updated_at.timestamp()}
            for uid, s in self._states.items()
        }

    @classmethod
    def from_dict(cls, data: dict[int, dict[str, float | int]]) -> OnboardingStateStore:
        store = cls()
        for uid, info in data.items():
            store._states[uid] = State(
                step=int(info["step"]),
                updated_at=datetime.fromtimestamp(
                    float(info["updated_at"]), tz=UTC
                ),
            )
        return store


async def reset_onboarding(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle ``/reset_onboarding`` command."""

    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return None
    store = cast(
        OnboardingStateStore,
        context.application.bot_data.setdefault("onb_state", OnboardingStateStore()),
    )
    store.reset(user.id)
    await message.reply_text("Onboarding reset.")
    return None


__all__ = ["OnboardingStateStore", "reset_onboarding"]
