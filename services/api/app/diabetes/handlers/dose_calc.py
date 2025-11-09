"""Handlers and conversation flow for insulin dose calculations."""

import asyncio
import datetime
import logging
from enum import IntEnum
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

from services.api.app.diabetes.gpt_command_parser import parse_command
from services.api.app.diabetes.services.db import (
    Profile,
    SessionLocal,
)
from services.api.app.diabetes.services.repository import commit
from services.api.app.diabetes.utils.constants import MAX_SUGAR_MMOL_L, XE_GRAMS
from services.api.app.diabetes.utils.calc_bolus import (
    PatientProfile,
    calc_bolus,
)
from services.api.app.diabetes.utils.functions import (
    _safe_float,
    smart_input,
)
from services.api.app.diabetes.utils.ui import (
    confirm_keyboard,
    dose_keyboard,
    dose_method_keyboard,
    PHOTO_BUTTON_PATTERN,
    SUGAR_BUTTON_TEXT,
    DOSE_BUTTON_TEXT,
    HISTORY_BUTTON_TEXT,
    REPORT_BUTTON_TEXT,
    PROFILE_BUTTON_TEXT,
    BACK_BUTTON_TEXT,
    SHORT_INSULIN_BUTTON_TEXT,
    LONG_INSULIN_BUTTON_TEXT,
)
from services.api.app.ui.keyboard import build_main_keyboard

from . import EntryData, UserData
from .alert_handlers import check_alert
from .common_handlers import menu_command
from .profile import profile_view
from .reporting_handlers import history_view, report_request, send_report

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

T = TypeVar("T")

MAX_INSULIN_UNITS = 200.0


class DoseState(IntEnum):
    TYPE = 2
    METHOD = 3
    XE = 4
    CARBS = 5
    SUGAR = 6
    LONG = 7


DOSE_TYPE, DOSE_METHOD, DOSE_XE, DOSE_CARBS, DOSE_SUGAR, DOSE_LONG = (
    DoseState.TYPE,
    DoseState.METHOD,
    DoseState.XE,
    DoseState.CARBS,
    DoseState.SUGAR,
    DoseState.LONG,
)
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
    await message.reply_text(
        "💉 Какую дозу хотите записать?",
        reply_markup=dose_keyboard,
    )
    return DoseState.TYPE


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
    text_lower = text.lower()
    if "назад" in text_lower:
        await message.reply_text(
            "💉 Какую дозу хотите записать?",
            reply_markup=dose_keyboard,
        )
        user_data.pop("pending_entry", None)
        return DoseState.TYPE
    if "углев" in text_lower:
        await message.reply_text(
            "Введите количество углеводов (г).",
            reply_markup=dose_method_keyboard,
        )
        return DoseState.CARBS
    if "xe" in text_lower or "хе" in text_lower:
        await message.reply_text(
            "Введите количество ХЕ.", reply_markup=dose_method_keyboard
        )
        return DoseState.XE
    await message.reply_text(
        "Пожалуйста, выберите метод: ХЕ или углеводы.",
        reply_markup=dose_method_keyboard,
    )
    return DoseState.METHOD


async def dose_type_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle insulin type selection before method choice."""
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
    text_lower = text.lower()
    short_token = SHORT_INSULIN_BUTTON_TEXT.lower()
    long_token = LONG_INSULIN_BUTTON_TEXT.lower()
    if "назад" in text_lower:
        return await dose_cancel(update, context)
    if "корот" in text_lower or text_lower.strip() == short_token:
        user_data.pop("pending_entry", None)
        await message.reply_text(
            "Как рассчитать короткий (болюс) инсулин? Выберите метод:",
            reply_markup=dose_method_keyboard,
        )
        return DoseState.METHOD
    if "длин" in text_lower or text_lower.strip() == long_token:
        user = update.effective_user
        if user is None:
            return END
        entry: EntryData = {
            "telegram_id": user.id,
            "event_time": datetime.datetime.now(datetime.timezone.utc),
        }
        user_data["pending_entry"] = entry
        await message.reply_text(
            "Введите дозу длинного (базального) инсулина (ед.)."
        )
        return DoseState.LONG
    await message.reply_text(
        "Пожалуйста, выберите короткий или длинный инсулин.",
        reply_markup=dose_keyboard,
    )
    return DoseState.TYPE


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
        return DoseState.XE
    if xe < 0:
        await message.reply_text("Количество ХЕ не может быть отрицательным.")
        return DoseState.XE
    entry: EntryData = {
        "telegram_id": user.id,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
        "xe": xe,
    }
    user_data["pending_entry"] = entry
    await message.reply_text("Введите текущий сахар (ммоль/л).")
    return DoseState.SUGAR


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
        return DoseState.CARBS
    if carbs < 0:
        await message.reply_text("Количество углеводов не может быть отрицательным.")
        return DoseState.CARBS
    entry: EntryData = {
        "telegram_id": user.id,
        "event_time": datetime.datetime.now(datetime.timezone.utc),
        "carbs_g": carbs,
    }
    user_data["pending_entry"] = entry
    await message.reply_text("Введите текущий сахар (ммоль/л).")
    return DoseState.SUGAR


async def dose_long(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Capture long (basal) insulin dose from user."""
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
    dose_value = _safe_float(text)
    if dose_value is None:
        await message.reply_text("Введите дозу длинного инсулина числом (ед.).")
        return DoseState.LONG
    if dose_value < 0:
        await message.reply_text("Доза длинного инсулина не может быть отрицательной.")
        return DoseState.LONG
    rounded_value = round(dose_value * 2) / 2
    if rounded_value > MAX_INSULIN_UNITS:
        await message.reply_text(
            f"Доза длинного инсулина не должна превышать {MAX_INSULIN_UNITS} ед."
        )
        return DoseState.LONG
    entry_raw = user_data.get("pending_entry")
    if not isinstance(entry_raw, dict):
        entry: EntryData = {
            "telegram_id": user.id,
            "event_time": datetime.datetime.now(datetime.timezone.utc),
        }
    else:
        entry = entry_raw
    entry["insulin_long"] = rounded_value
    user_data["pending_entry"] = entry
    short_val = entry.get("insulin_short")
    short_info = (
        f"Короткий (болюс) — {short_val} ед." if short_val is not None else "Короткий не вводился."
    )
    await message.reply_text(
        f"Подтвердите: длинный (базал) — {rounded_value} ед. {short_info}",
        reply_markup=confirm_keyboard(),
    )
    return END


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
        return DoseState.SUGAR
    if sugar < 0:
        await message.reply_text("Сахар не может быть отрицательным.")
        return DoseState.SUGAR
    if sugar > MAX_SUGAR_MMOL_L:
        await message.reply_text(
            f"Сахар не должен превышать {MAX_SUGAR_MMOL_L} ммоль/л."
        )
        return DoseState.SUGAR

    entry = user_data.get("pending_entry")
    if entry is None or ("xe" not in entry and "carbs_g" not in entry):
        await message.reply_text(
            "Сначала укажите углеводы или ХЕ.",
            reply_markup=dose_keyboard,
        )
        user_data.pop("pending_entry", None)
        return DoseState.METHOD

    entry["sugar_before"] = sugar
    xe = entry.get("xe")
    carbs_g = entry.get("carbs_g")
    if carbs_g is None and xe is None:
        await message.reply_text(
            "Не указаны углеводы или ХЕ. Расчёт невозможен.",
            reply_markup=build_main_keyboard(),
        )
        user_data.pop("pending_entry", None)
        return END
    if carbs_g is None and xe is not None:
        carbs_g = XE_GRAMS * xe
        entry["carbs_g"] = carbs_g

    user_id = user.id
    if run_db is None:

        def _get_profile() -> Profile | None:
            with SessionLocal() as session:
                return session.get(Profile, user_id)

        profile = await asyncio.to_thread(_get_profile)
    else:
        profile = cast(
            Profile | None,
            await run_db(
                lambda s: s.get(Profile, user_id),
                sessionmaker=SessionLocal,
            ),
        )

    if (
        profile is None
        or profile.icr is None
        or profile.cf is None
        or profile.target_bg is None
    ):
        await message.reply_text(
            "Профиль не настроен. Установите коэффициенты через /profile.",
            reply_markup=build_main_keyboard(),
        )
        user_data.pop("pending_entry", None)
        return END

    diabetes_type = getattr(profile, "diabetes_type", "")
    if diabetes_type in {"unknown", "t2_no"}:
        await message.reply_text(
            "Для указанного типа диабета расчёт дозы недоступен.",
            reply_markup=build_main_keyboard(),
        )
        user_data.pop("pending_entry", None)
        return END

    patient = PatientProfile(
        icr=profile.icr,
        cf=profile.cf,
        target_bg=profile.target_bg,
    )
    if carbs_g is None:
        await message.reply_text(
            "Не указаны углеводы или ХЕ. Расчёт невозможен.",
            reply_markup=build_main_keyboard(),
        )
        user_data.pop("pending_entry", None)
        return END
    try:
        dose = calc_bolus(carbs_g, sugar, patient)
    except ValueError:
        await message.reply_text(
            "Некорректные коэффициенты в профиле. Настройте их через /profile.",
            reply_markup=build_main_keyboard(),
        )
        user_data.pop("pending_entry", None)
        return END
    entry["dose"] = dose
    entry["insulin_short"] = dose

    user_data["pending_entry"] = entry

    xe_info = f", ХЕ: {xe}" if xe is not None else ""
    long_val = entry.get("insulin_long")
    summary = (
        f"💉 Расчёт завершён:\n"
        f"• Углеводы: {carbs_g} г{xe_info}\n"
        f"• Сахар: {sugar} ммоль/л\n"
        f"• Короткий (болюс): {dose} Ед\n"
    )
    if long_val is not None:
        summary += f"• Длинный (базал): {long_val} ед\n"
    summary += "\nСохранить это в дневник?"
    await message.reply_text(summary, reply_markup=confirm_keyboard())
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
    await message.reply_text("Отменено.", reply_markup=build_main_keyboard())
    user_data.pop("pending_entry", None)
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
from .sugar_handlers import (  # noqa: E402
    SUGAR_VAL,
    sugar_start,
    sugar_val,
    sugar_conv,
    prompt_sugar,
)
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
    """Handle freeform text commands within dose calculation context."""
    await _gpt_handlers.freeform_handler(
        update,
        context,
        SessionLocal=SessionLocal,
        commit=commit,
        check_alert=check_alert,
        menu_keyboard_markup=build_main_keyboard(),
        smart_input=smart_input,
        parse_command=parse_command,
        send_report=send_report,
    )


chat_with_gpt = _gpt_handlers.chat_with_gpt


dose_conv = ConversationHandler(
    entry_points=[
        CommandHandler("dose", dose_start),
        MessageHandler(filters.Regex(f"^{DOSE_BUTTON_TEXT}$"), dose_start),
    ],
    states={
        DoseState.TYPE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, dose_type_choice)
        ],
        DoseState.METHOD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, dose_method_choice)
        ],
        DoseState.XE: [
            MessageHandler(filters.Regex(r"^-?\d+(?:[.,]\d+)?$"), dose_xe)
        ],
        DoseState.CARBS: [
            MessageHandler(filters.Regex(r"^-?\d+(?:[.,]\d+)?$"), dose_carbs)
        ],
        DoseState.SUGAR: [
            MessageHandler(filters.Regex(r"^-?\d+(?:[.,]\d+)?$"), dose_sugar)
        ],
        DoseState.LONG: [
            MessageHandler(filters.Regex(r"^-?\d+(?:[.,]\d+)?$"), dose_long)
        ],
        PHOTO_SUGAR: [
            MessageHandler(
                filters.Regex(r"^-?\d+(?:[.,]\d+)?$"),
                dose_sugar,
            )
        ],
    },
    fallbacks=[
        MessageHandler(filters.Regex(f"^{BACK_BUTTON_TEXT}$"), dose_cancel),
        CommandHandler("menu", _cancel_then(menu_command)),
        MessageHandler(
            filters.Regex(PHOTO_BUTTON_PATTERN),
            _cancel_then(photo_prompt),
        ),
        MessageHandler(
            filters.Regex(f"^{SUGAR_BUTTON_TEXT}$"),
            _cancel_then(sugar_start),
        ),
        MessageHandler(
            filters.Regex(f"^{HISTORY_BUTTON_TEXT}$"),
            _cancel_then(history_view),
        ),
        MessageHandler(
            filters.Regex(f"^{REPORT_BUTTON_TEXT}$"),
            _cancel_then(report_request),
        ),
        MessageHandler(
            filters.Regex(f"^{PROFILE_BUTTON_TEXT}$"),
            _cancel_then(profile_view),
        ),
    ],
)

prompt_dose = dose_start

__all__ = [
    "SessionLocal",
    "DoseState",
    "DOSE_METHOD",
    "DOSE_XE",
    "DOSE_CARBS",
    "DOSE_SUGAR",
    "DOSE_TYPE",
    "DOSE_LONG",
    "END",
    "dose_start",
    "dose_type_choice",
    "dose_method_choice",
    "dose_xe",
    "dose_carbs",
    "dose_long",
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
