"""Learning mode onboarding utilities."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes


async def ensure_overrides(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """Ensure learning mode is allowed for the user.

    This is a stub implementation that always allows learning mode.
    """

    return True

