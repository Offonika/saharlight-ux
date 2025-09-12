"""Inline assistant menu with callback handlers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypeAlias, cast, MutableMapping

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ContextTypes,
    ExtBot,
    JobQueue,
)

from services.api.app.diabetes.utils.ui import BACK_BUTTON_TEXT
from services.api.app.diabetes.assistant_state import AWAITING_KIND, set_last_mode
from services.api.app.diabetes.labs_handlers import AWAITING_KIND as LABS_AWAITING_KIND
from services.api.app.diabetes import visit_handlers
from services.api.app.assistant.services import memory_service

__all__ = [
    "assistant_keyboard",
    "show_menu",
    "assistant_callback",
    "ASSISTANT_HANDLER",
    "post_init",
]

MENU_LAYOUT: tuple[tuple[InlineKeyboardButton, ...], ...] = (
    (InlineKeyboardButton("🎓 Обучение", callback_data="asst:learn"),),
    (InlineKeyboardButton("💬 Чат", callback_data="asst:chat"),),
    (InlineKeyboardButton("🧪 Анализы", callback_data="asst:labs"),),
    (InlineKeyboardButton("🩺 Визит", callback_data="asst:visit"),),
)

MODE_TEXTS: dict[str, str] = {
    "learn": "Режим обучения активирован.",
    "chat": "Свободный диалог активирован.",
    "labs": "Пришлите файл или текст анализов.",
    "visit": "Подготовка чек-листа визита.",
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
    logging.info(
        "assistant_mode_selected",
        extra={"mode": mode, "user_id": getattr(user, "id", None)},
    )
    text = MODE_TEXTS.get(mode, "Неизвестная команда.")
    if message and hasattr(message, "edit_text"):
        await cast(Message, message).edit_text(text, reply_markup=_back_keyboard())
    user_data = cast(dict[str, object], ctx.user_data)
    if mode == "labs":
        user_data["waiting_labs"] = True
        user_data.pop(LABS_AWAITING_KIND, None)
        user_data[AWAITING_KIND] = "labs"
        set_last_mode(user_data, None)
        if user is not None:
            await memory_service.set_last_mode(user.id, None)
    else:
        user_data[AWAITING_KIND] = mode
        set_last_mode(user_data, mode)
        if user is not None:
            await memory_service.set_last_mode(user.id, mode)
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
    """Restore last assistant mode for users and show corresponding state."""

    from services.api.app.diabetes.assistant_state import LAST_MODE_KEY

    user_map = cast(MutableMapping[int, dict[str, object]], app.user_data)
    modes = await memory_service.get_all_last_modes()
    for user_id, mode in modes:
        data = user_map.setdefault(user_id, {})
        data[LAST_MODE_KEY] = mode
        data[AWAITING_KIND] = mode
        text = MODE_TEXTS.get(mode, "Ассистент:")
        markup = _back_keyboard() if mode in MODE_TEXTS else assistant_keyboard()
        try:
            await app.bot.send_message(
                chat_id=user_id, text=text, reply_markup=markup
            )
        except Exception:  # pragma: no cover - logging
            logging.exception("Failed to restore assistant mode", extra={"user_id": user_id})
