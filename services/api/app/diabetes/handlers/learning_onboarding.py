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

from ..learning_onboarding import ensure_overrides, learn_reset

__all__ = ["onboarding_reply", "register_handlers", "learn_reset"]

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
    message: Message | None = update.message
    text: str | None = None
    if message is not None and message.text:
        text = message.text.strip()
    else:
        query = update.callback_query
        if query is None or query.data is None or query.message is None:
            return
        await query.answer()
        if isinstance(query.message, Message):
            message = query.message
        text = query.data.strip()
    if text is None:
        return
    user_data = cast(dict[str, object], context.user_data)
    stage = cast(str | None, user_data.get("learn_onboarding_stage"))
    if stage is None:
        return
    overrides = cast(
        dict[str, str], user_data.setdefault("learn_profile_overrides", {})
    )
    if text.startswith("ll:"):
        text = text.split(":", 1)[1]
    overrides[stage] = text
    user_data.pop("learn_onboarding_stage", None)
    if await ensure_overrides(update, context) and message is not None:
        await message.reply_text("Ответы сохранены. Отправьте /learn чтобы продолжить.")


def register_handlers(app: App) -> None:
    """Register learning onboarding handlers on the application."""
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_reply))
    app.add_handler(CallbackQueryHandler(onboarding_reply, pattern="^ll:"))
    app.add_handler(CommandHandler("learn_reset", learn_reset))
