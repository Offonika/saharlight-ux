import datetime
import logging
from collections.abc import Awaitable, Callable, Coroutine
from typing import TypeVar, cast

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from services.api.app.diabetes.services.db import (
    Profile,
    SessionLocal,
)

try:
    from services.api.app.diabetes.services.db import run_db as _run_db
except Exception:  # pragma: no cover - optional db runner
    run_db: Callable[..., Awaitable[object]] | None = None
else:
    run_db = cast(Callable[..., Awaitable[object]], _run_db)
from services.api.app.diabetes.services.repository import commit
from services.api.app.diabetes.utils.functions import (
    PatientProfile,
    _safe_float,
    calc_bolus,
    smart_input,
)
from services.api.app.diabetes.utils.constants import XE_GRAMS
from services.api.app.diabetes.utils.ui import (
    confirm_keyboard,
    dose_keyboard,
    menu_keyboard,
)

from .common_handlers import menu_command
from .profile import profile_view
from services.api.app.diabetes.gpt_command_parser import parse_command
from .alert_handlers import check_alert
from .reporting_handlers import history_view, report_request, send_report
from . import EntryData, UserData

logger = logging.getLogger(__name__)

T = TypeVar("T")

DOSE_METHOD, DOSE_XE, DOSE_CARBS, DOSE_SUGAR = range(3, 7)
END: int = ConversationHandler.END


async def dose_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for dose calculation conversation."""
    user_data_raw = context.user_data
    if user_data_raw is None:
        return END
    user_data = cast(UserData, user_data_raw)
    message = update.message
    if message is None:
        return END
    user_data.pop("pending_entry", None)
    user_data.pop("edit_id", None)
    user_data.pop("dose_method", None)
    await message.reply_text(
        "💉 Как рассчитать дозу? Выберите метод:",
        reply_markup=dose_keyboard,
    )
    return DOSE_METHOD


async def dose_method_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle method selection for dose calculation."""
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
    text = text.lower()
    if "назад" in text:
        return await dose_cancel(update, context)
    if "углев" in text:
        user_data["dose_method"] = "carbs"
        await message.reply_text("Введите количество углеводов (г).")
        return DOSE_CARBS
    if "xe" in text or "хе" in text:
        user_data["dose_method"] = "xe"
        await message.reply_text("Введите количество ХЕ.")
        return DOSE_XE
    await message.reply_text(
        "Пожалуйста, выберите метод: ХЕ или углеводы.",
        reply_markup=dose_keyboard,
    )
    return DOSE_METHOD


async def dose_xe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Capture XE amount from user."""
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
    xe = _safe_float(text)
    if xe is None:
        await message.reply_text("Введите число ХЕ.")
        return DOSE_XE
    if xe < 0:
        await message.reply_text("Количество ХЕ не может быть отрицательным.")
        return DOSE_XE
    entry: EntryData = {
        "telegram_id": user.id,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
        "xe": xe,
    }
    user_data["pending_entry"] = entry
    await message.reply_text("Введите текущий сахар (ммоль/л).")
    return DOSE_SUGAR


async def dose_carbs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Capture carbohydrates in grams."""
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
    carbs = _safe_float(text)
    if carbs is None:
        await message.reply_text("Введите углеводы числом в граммах.")
        return DOSE_CARBS
    if carbs < 0:
        await message.reply_text("Количество углеводов не может быть отрицательным.")
        return DOSE_CARBS
    entry: EntryData = {
        "telegram_id": user.id,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
        "carbs_g": carbs,
    }
    user_data["pending_entry"] = entry
    await message.reply_text("Введите текущий сахар (ммоль/л).")
    return DOSE_SUGAR


async def dose_sugar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Finalize dose calculation after receiving sugar level."""
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
        return DOSE_SUGAR
    if sugar < 0:
        await message.reply_text("Сахар не может быть отрицательным.")
        return DOSE_SUGAR

    entry = cast(EntryData, user_data.get("pending_entry", {}))
    entry["sugar_before"] = sugar
    xe = entry.get("xe")
    carbs_g = entry.get("carbs_g")
    if carbs_g is None and xe is None:
        await message.reply_text(
            "Не указаны углеводы или ХЕ. Расчёт невозможен.",
            reply_markup=menu_keyboard,
        )
        user_data.pop("pending_entry", None)
        return END
    if carbs_g is None and xe is not None:
        carbs_g = XE_GRAMS * xe
        entry["carbs_g"] = carbs_g

    user_id = user.id
    if run_db is None:
        with SessionLocal() as session:
            profile = session.get(Profile, user_id)
    else:
        profile = await run_db(
            lambda s: s.get(Profile, user_id),
            sessionmaker=SessionLocal,
        )

    if (
        profile is None
        or profile.icr is None
        or profile.cf is None
        or profile.target_bg is None
    ):
        await message.reply_text(
            "Профиль не настроен. Установите коэффициенты через /profile.",
            reply_markup=menu_keyboard,
        )
        user_data.pop("pending_entry", None)
        return END

    patient = PatientProfile(
        icr=profile.icr,
        cf=profile.cf,
        target_bg=profile.target_bg,
    )
    dose = calc_bolus(carbs_g, sugar, patient)
    entry["dose"] = dose

    user_data["pending_entry"] = entry

    xe_info = f", ХЕ: {xe}" if xe is not None else ""
    await message.reply_text(
        text=(
            f"💉 Расчёт завершён:\n"
            f"• Углеводы: {carbs_g} г{xe_info}\n"
            f"• Сахар: {sugar} ммоль/л\n"
            f"• Ваша доза: {dose} Ед\n\n"
            "Сохранить это в дневник?"
        ),
        reply_markup=confirm_keyboard(),
    )
    return END


async def dose_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel dose calculation conversation."""
    user_data_raw = context.user_data
    if user_data_raw is None:
        return END
    user_data = cast(UserData, user_data_raw)
    message = update.message
    if message is None:
        return END
    await message.reply_text("Отменено.", reply_markup=menu_keyboard)
    user_data.pop("pending_entry", None)
    user_data.pop("dose_method", None)
    chat_data = getattr(context, "chat_data", None)
    if chat_data is not None:
        chat_data.pop("sugar_active", None)
    return END


def _cancel_then(
    handler: Callable[
        [Update, ContextTypes.DEFAULT_TYPE], Coroutine[object, object, T]
    ],
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Coroutine[object, object, T]]:
    """Return a wrapper calling ``dose_cancel`` before ``handler``."""

    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE) -> T:
        await dose_cancel(update, context)
        return await handler(update, context)

    return wrapped


# Import additional handlers after defining dose_cancel to avoid circular imports
from .sugar_handlers import (
    SUGAR_VAL,
    sugar_start,
    sugar_val,
    sugar_conv,
    prompt_sugar,
)  # noqa: E402
from .photo_handlers import (  # noqa: E402
    PHOTO_SUGAR,
    WAITING_GPT_FLAG,
    doc_handler,
    photo_handler,
    photo_prompt,
    prompt_photo,
)
from . import gpt_handlers as _gpt_handlers  # noqa: E402


async def freeform_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    return await _gpt_handlers.freeform_handler(
        update,
        context,
        SessionLocal=SessionLocal,
        commit=commit,
        check_alert=check_alert,
        menu_keyboard=menu_keyboard,
        smart_input=smart_input,
        parse_command=parse_command,
        send_report=send_report,
    )


chat_with_gpt = _gpt_handlers.chat_with_gpt


dose_conv = ConversationHandler(
    entry_points=[
        CommandHandler("dose", dose_start),
        MessageHandler(filters.Regex("^💉 Доза инсулина$"), dose_start),
    ],
    states={
        DOSE_METHOD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, dose_method_choice)
        ],
        DOSE_XE: [MessageHandler(filters.Regex(r"^-?\d+(?:[.,]\d+)?$"), dose_xe)],
        DOSE_CARBS: [MessageHandler(filters.Regex(r"^-?\d+(?:[.,]\d+)?$"), dose_carbs)],
        DOSE_SUGAR: [MessageHandler(filters.Regex(r"^-?\d+(?:[.,]\d+)?$"), dose_sugar)],
    },
    fallbacks=[
        MessageHandler(filters.Regex("^↩️ Назад$"), dose_cancel),
        CommandHandler("menu", cast(object, _cancel_then(menu_command))),
        MessageHandler(
            filters.Regex("^📷 Фото еды$"), cast(object, _cancel_then(photo_prompt))
        ),
        MessageHandler(
            filters.Regex("^🩸 Уровень сахара$"),
            cast(object, _cancel_then(sugar_start)),
        ),
        MessageHandler(
            filters.Regex("^📊 История$"), cast(object, _cancel_then(history_view))
        ),
        MessageHandler(
            filters.Regex("^📈 Отчёт$"), cast(object, _cancel_then(report_request))
        ),
        MessageHandler(
            filters.Regex("^📄 Мой профиль$"), cast(object, _cancel_then(profile_view))
        ),
    ],
)

prompt_dose = dose_start

__all__ = [
    "SessionLocal",
    "DOSE_METHOD",
    "DOSE_XE",
    "DOSE_CARBS",
    "DOSE_SUGAR",
    "END",
    "dose_start",
    "dose_method_choice",
    "dose_xe",
    "dose_carbs",
    "dose_sugar",
    "dose_cancel",
    "_cancel_then",
    "dose_conv",
    "prompt_dose",
    "commit",
    "parse_command",
    "smart_input",
    "send_report",
    # re-exported handlers
    "photo_prompt",
    "photo_handler",
    "doc_handler",
    "prompt_photo",
    "sugar_start",
    "sugar_val",
    "sugar_conv",
    "prompt_sugar",
    "freeform_handler",
    "chat_with_gpt",
    "PHOTO_SUGAR",
    "SUGAR_VAL",
    "WAITING_GPT_FLAG",
]
