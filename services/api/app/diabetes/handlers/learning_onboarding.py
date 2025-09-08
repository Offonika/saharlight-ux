from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypeAlias, cast

from telegram import Message, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ExtBot,
    JobQueue,
    MessageHandler,
    filters,
)

from ..learning_onboarding import CB_PREFIX, ensure_overrides, learn_reset

__all__ = [
    "CB_PREFIX",
    "onboarding_reply",
    "onboarding_callback",
    "register_handlers",
    "learn_reset",
]

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
    message = update.message
    if message is None or not message.text:
        return
    user_data = cast(dict[str, object], context.user_data)
    stage = cast(str | None, user_data.get("learn_onboarding_stage"))
    if stage is None:
        return
    overrides = cast(
        dict[str, str], user_data.setdefault("learn_profile_overrides", {})
    )
    overrides[stage] = message.text.strip()
    user_data.pop("learn_onboarding_stage", None)
    if await ensure_overrides(update, context):
        await message.reply_text("Ответы сохранены. Отправьте /learn чтобы продолжить.")


async def onboarding_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button presses during learning onboarding."""
    logger.debug("onboarding_callback", extra={"user": update.effective_user})
    query = update.callback_query
    if query is None or query.data is None:
        return
    await query.answer()
    user_data = cast(dict[str, object], context.user_data)
    stage = cast(str | None, user_data.get("learn_onboarding_stage"))
    if stage is None:
        return
    data = query.data.removeprefix(CB_PREFIX)
    overrides = cast(
        dict[str, str], user_data.setdefault("learn_profile_overrides", {})
    )
    overrides[stage] = data
    user_data.pop("learn_onboarding_stage", None)
    if await ensure_overrides(update, context):
        message = cast("Message | None", query.message)
        if message is not None:
            await message.reply_text(
                "Ответы сохранены. Отправьте /learn чтобы продолжить."
            )


def register_handlers(app: App) -> None:
    """Register learning onboarding handlers on the application."""
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_reply))
    app.add_handler(CallbackQueryHandler(onboarding_callback, pattern=f"^{CB_PREFIX}"))
    app.add_handler(CommandHandler("learn_reset", learn_reset))
