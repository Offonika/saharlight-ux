from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypeAlias

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ExtBot,
    JobQueue,
    MessageHandler,
    filters,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    App: TypeAlias = Application[
        ExtBot[None],
        ContextTypes.DEFAULT_TYPE,
        dict[str, object],
        dict[str, object],
        dict[str, object],
        JobQueue[ContextTypes.DEFAULT_TYPE],
    ]
else:
    App = Application


async def onboarding_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user replies during learning onboarding."""
    logger.debug("onboarding_reply", extra={"user": update.effective_user})


async def learn_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset learning-related state for the user."""
    logger.debug("learn_reset", extra={"user": update.effective_user})


def register_handlers(app: App) -> None:
    """Register learning onboarding handlers on the application."""
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_reply))
    app.add_handler(CommandHandler("learn_reset", learn_reset))

