from __future__ import annotations

import logging
import re
from typing import MutableMapping, Sequence, cast

from telegram import Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

from services.api.app.diabetes.assistant_state import get_last_mode, set_last_mode
from services.api.app.diabetes import learning_handlers
from services.api.app.diabetes.handlers import gpt_handlers
from services.api.app.diabetes.utils.ui import (
    HELP_BUTTON_TEXT,
    PHOTO_BUTTON_PATTERN,
    QUICK_INPUT_BUTTON_TEXT,
    REPORT_BUTTON_TEXT,
    SUGAR_BUTTON_TEXT,
    DOSE_BUTTON_TEXT,
    HISTORY_BUTTON_TEXT,
    SOS_BUTTON_TEXT,
    SUBSCRIPTION_BUTTON_TEXT,
)
from services.api.app.ui.keyboard import LEARN_BUTTON_TEXT

logger = logging.getLogger(__name__)

BOTTOM_BUTTON_PATTERNS: Sequence[re.Pattern[str]] = (
    PHOTO_BUTTON_PATTERN,
    re.compile(re.escape(SUGAR_BUTTON_TEXT)),
    re.compile(re.escape(DOSE_BUTTON_TEXT)),
    re.compile(re.escape(HISTORY_BUTTON_TEXT)),
    re.compile(re.escape(REPORT_BUTTON_TEXT)),
    re.compile(re.escape(QUICK_INPUT_BUTTON_TEXT)),
    re.compile(re.escape(HELP_BUTTON_TEXT)),
    re.compile(re.escape(SOS_BUTTON_TEXT)),
    re.compile(re.escape(SUBSCRIPTION_BUTTON_TEXT)),
    re.compile(re.escape(LEARN_BUTTON_TEXT)),
)


async def on_any_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route arbitrary text based on the assistant's ``last_mode``."""

    message = update.message
    if message is None or message.text is None:
        return
    text = message.text
    for pattern in BOTTOM_BUTTON_PATTERNS:
        if pattern.match(text):
            return
    user_data = cast(MutableMapping[str, object], context.user_data or {})
    mode = get_last_mode(user_data)
    logger.debug("assistant_router mode=%s text=%s", mode, text)
    if mode == "learn":
        await learning_handlers.on_any_text(update, context)
        raise ApplicationHandlerStop
    if mode == "chat":
        await gpt_handlers.freeform_handler(update, context)
        raise ApplicationHandlerStop
    if mode == "labs":
        user_data["waiting_labs"] = True
        await message.reply_text("Отправьте анализы в виде файла или текста.")
        set_last_mode(user_data, None)
        raise ApplicationHandlerStop
    if mode == "visit":
        await message.reply_text(
            "Чек-лист визита: измерения, вопросы врачу, назначения."
        )
        set_last_mode(user_data, None)
        raise ApplicationHandlerStop


__all__ = ["on_any_text"]
