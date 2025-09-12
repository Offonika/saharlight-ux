"""Inline assistant menu with callback handlers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, MutableMapping, TypeAlias, cast

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ContextTypes,
    ExtBot,
    JobQueue,
)

from services.api.app.assistant.assistant_menu import render_assistant_menu
from services.api.app.config import get_settings

from services.api.app.assistant.services import memory_service
from services.api.app.diabetes.utils.ui import BACK_BUTTON_TEXT
from services.api.app.diabetes.assistant_state import AWAITING_KIND, set_last_mode
from services.api.app.diabetes.labs_handlers import AWAITING_KIND as LABS_AWAITING_KIND
from services.api.app.diabetes import visit_handlers

logger = logging.getLogger(__name__)

__all__ = [
    "assistant_keyboard",
    "show_menu",
    "assistant_callback",
    "post_init",
    "ASSISTANT_HANDLER",
]

_settings = get_settings()
_menu_texts = render_assistant_menu(_settings.assistant_menu_emoji)

MENU_LAYOUT: tuple[tuple[InlineKeyboardButton, ...], ...] = (
    (InlineKeyboardButton(_menu_texts.learn, callback_data="asst:learn"),),
    (InlineKeyboardButton(_menu_texts.chat, callback_data="asst:chat"),),
    (InlineKeyboardButton(_menu_texts.labs, callback_data="asst:labs"),),
    (InlineKeyboardButton(_menu_texts.visit, callback_data="asst:visit"),),
)

MODE_TEXTS: dict[str, str] = {
    "learn": (
        "Режим обучения активирован. Спрашивайте о продуктах и дозах. "
        "Присылайте фото — я посчитаю хлебные единицы. 📚"
    ),
    "chat": (
        "Свободный диалог активирован. Делитесь вопросами или переживаниями. "
        "Просто поговорим или обсудим диабет. 💬"
    ),
    "labs": (
        "Пришлите файл или текст анализов. Я помогу расшифровать показатели и дам "
        "общие советы. Можно отправить несколько сообщений. 🧪"
    ),
    "visit": (
        "Подготовка чек-листа визита. Я спрошу про анализы и самочувствие. "
        "Ответьте на вопросы, чтобы получить PDF. 📄"
    ),
}


def assistant_keyboard() -> InlineKeyboardMarkup:
    """Build assistant menu keyboard."""

    return InlineKeyboardMarkup(MENU_LAYOUT)


async def show_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply with the assistant menu."""

    message = update.effective_message
    if message:
        await message.reply_text("Ассистент:", reply_markup=assistant_keyboard())


def _back_keyboard() -> InlineKeyboardMarkup:
    """Create a back button keyboard."""

    return InlineKeyboardMarkup(
        ((InlineKeyboardButton(BACK_BUTTON_TEXT, callback_data="asst:back"),),)
    )


async def post_init(
    app: Application[
        ExtBot[None],
        ContextTypes.DEFAULT_TYPE,
        dict[str, object],
        dict[str, object],
        dict[str, object],
        DefaultJobQueue,
    ],
) -> None:
    """Restore last assistant modes for users on startup."""

    records = await memory_service.get_last_modes()
    store = cast(MutableMapping[int, dict[str, object]], app.user_data)
    for user_id, mode in records:
        if mode not in MODE_TEXTS:
            continue
        data = store.setdefault(user_id, {})
        data[AWAITING_KIND] = mode
        set_last_mode(data, mode)
        await app.bot.send_message(
            chat_id=user_id,
            text=MODE_TEXTS[mode],
            reply_markup=_back_keyboard(),
        )


async def assistant_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle assistant menu callbacks."""

    query = update.callback_query
    if query is None or query.data is None:
        return
    data = query.data
    message = query.message
    await query.answer()
    if data == "asst:save_note":
        await visit_handlers.save_note_callback(update, ctx)
        return
    if data in {"asst:back", "asst:menu"}:
        if message and hasattr(message, "edit_text"):
            await cast(Message, message).edit_text(
                "Ассистент:", reply_markup=assistant_keyboard()
            )
        return
    mode = data.split(":", 1)[1]
    user = getattr(update, "effective_user", None)
    user_id = getattr(user, "id", None)
    if mode not in MODE_TEXTS:
        logger.warning(
            "assistant_unknown_callback",
            extra={"data": data, "user_id": getattr(user, "id", None)},
        )
        if message and hasattr(message, "edit_text"):
            await cast(Message, message).edit_text(
                "Неизвестная команда.", reply_markup=_back_keyboard()
            )
        return
    logger.info(
        "assistant_mode_selected",
        extra={"mode": mode, "user_id": getattr(user, "id", None)},
    )
    if message and hasattr(message, "edit_text"):
        await cast(Message, message).edit_text(
            MODE_TEXTS[mode], reply_markup=_back_keyboard()
        )
    user_data = cast(dict[str, object], ctx.user_data)
    if mode == "labs":
        user_data["waiting_labs"] = True
        user_data.pop(LABS_AWAITING_KIND, None)
        user_data[AWAITING_KIND] = "labs"
        set_last_mode(user_data, None)
        if isinstance(user_id, int):
            await memory_service.set_last_mode(user_id, None)
    else:
        user_data[AWAITING_KIND] = mode
        set_last_mode(user_data, mode)
        if isinstance(user_id, int):
            await memory_service.set_last_mode(user_id, mode)
        if mode == "visit":
            await visit_handlers.send_checklist(update, ctx)
            return


if TYPE_CHECKING:
    CallbackQueryHandlerT: TypeAlias = CallbackQueryHandler[
        ContextTypes.DEFAULT_TYPE, object
    ]
    DefaultJobQueue: TypeAlias = JobQueue[ContextTypes.DEFAULT_TYPE]
else:
    CallbackQueryHandlerT = CallbackQueryHandler
    DefaultJobQueue = JobQueue

ASSISTANT_HANDLER = CallbackQueryHandlerT(assistant_callback, pattern="^asst:")
