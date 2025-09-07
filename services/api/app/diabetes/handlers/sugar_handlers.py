import datetime
import logging
from collections.abc import Awaitable, Callable
from typing import cast

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from sqlalchemy.orm import Session

from services.api.app.diabetes.services.db import Entry, SessionLocal
from services.api.app.diabetes.services.repository import CommitError, commit
from services.api.app.diabetes.utils.functions import _safe_float
from services.api.app.diabetes.utils.ui import (
    sugar_keyboard,
    SUGAR_BUTTON_TEXT,
    BACK_BUTTON_TEXT,
    PHOTO_BUTTON_TEXT,
)
from services.api.app.ui.keyboard import build_main_keyboard

from . import EntryData, UserData
from .alert_handlers import check_alert
from .common_handlers import menu_command
from .dose_calc import _cancel_then, dose_cancel
from .photo_handlers import photo_prompt

run_db: Callable[..., Awaitable[object]] | None
try:
    from services.api.app.diabetes.services.db import run_db as _run_db
except ImportError:  # pragma: no cover - optional db runner
    logging.getLogger(__name__).info(
        "run_db is unavailable; proceeding without async DB runner"
    )
    run_db = None
else:
    run_db = cast(Callable[..., Awaitable[object]], _run_db)

logger = logging.getLogger(__name__)

SUGAR_VAL = 8
END = ConversationHandler.END


async def sugar_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt user for current sugar level."""
    user_data_raw = context.user_data
    if user_data_raw is None:
        return END
    user_data = cast(UserData, user_data_raw)
    message = update.message
    if message is None:
        return END
    user = update.effective_user
    if user is None:
        return END
    user_data.pop("pending_entry", None)
    pending_entry: EntryData = {
        "telegram_id": user.id,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
    }
    user_data["pending_entry"] = pending_entry
    chat_data = getattr(context, "chat_data", None)
    if chat_data is not None:
        chat_data["sugar_active"] = True
    await message.reply_text(
        "Введите текущий уровень сахара (ммоль/л).", reply_markup=sugar_keyboard
    )
    return SUGAR_VAL


async def sugar_val(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store the provided sugar level to the diary."""
    chat_data = getattr(context, "chat_data", None)
    if chat_data is not None and not chat_data.get("sugar_active"):
        return END
    user_data_raw = context.user_data
    if user_data_raw is None:
        return END
    user_data = cast(UserData, user_data_raw)
    message = update.message
    if message is None:
        return END
    text = message.text
    if text is None:
        return END
    user = update.effective_user
    if user is None:
        return END
    sugar = _safe_float(text)
    if sugar is None:
        await message.reply_text("Введите сахар числом в ммоль/л.")
        return SUGAR_VAL
    if sugar < 0:
        await message.reply_text("Сахар не может быть отрицательным.")
        return SUGAR_VAL
    entry_data = cast(
        EntryData,
        user_data.pop("pending_entry", None)
        or {
            "telegram_id": user.id,
            "event_time": datetime.datetime.now(datetime.timezone.utc),
        },
    )
    entry_data["sugar_before"] = sugar

    def save_entry(session: Session, data: EntryData) -> bool:
        entry = Entry(**data)
        session.add(entry)
        try:
            commit(session)
        except CommitError:
            return False
        return True

    if run_db is None:
        with SessionLocal() as session:
            success = save_entry(session, entry_data)
    else:
        success = await run_db(save_entry, entry_data)
    if not success:
        await message.reply_text("⚠️ Не удалось сохранить запись.")
        return END
    await check_alert(update, context, sugar)
    await message.reply_text(
        f"✅ Уровень сахара {sugar} ммоль/л сохранён.",
        reply_markup=build_main_keyboard(),
    )
    if chat_data is not None:
        chat_data.pop("sugar_active", None)
    return END


prompt_sugar = sugar_start

sugar_conv = ConversationHandler(
    entry_points=[
        CommandHandler("sugar", sugar_start),
        MessageHandler(filters.Regex(f"^{SUGAR_BUTTON_TEXT}$"), sugar_start),
    ],
    states={
        SUGAR_VAL: [MessageHandler(filters.Regex(r"^-?\d+(?:[.,]\d+)?$"), sugar_val)],
    },
    fallbacks=[
        MessageHandler(filters.Regex(f"^{BACK_BUTTON_TEXT}$"), dose_cancel),
        CommandHandler("menu", cast(object, _cancel_then(menu_command))),
        MessageHandler(
            filters.Regex(f"^{PHOTO_BUTTON_TEXT}$"), cast(object, _cancel_then(photo_prompt))
        ),
    ],
)

__all__ = ["SUGAR_VAL", "sugar_start", "sugar_val", "sugar_conv", "prompt_sugar"]
