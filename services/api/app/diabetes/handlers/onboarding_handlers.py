"""Simplified onboarding conversation.

Implements three steps with navigation and progress hints:

1. Profile selection via inline buttons.
2. Timezone input with optional WebApp auto-detect button.
3. Reminder presets with ability to finish.
"""

from __future__ import annotations

import logging
import warnings
from typing import Any, Iterable, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from datetime import time as time_cls

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    Update,
    WebAppData,
)
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    ExtBot,
    MessageHandler,
    filters,
)
from telegram.warnings import PTBUserWarning

import config
from services.api.app.diabetes.services.db import SessionLocal, User, run_db
from services.api.app.diabetes.services.repository import commit
from services.api.app.diabetes.services.users import ensure_user_exists
from services.api.app.services import onboarding_state
from ..onboarding_state import OnboardingStateStore
from services.api.app.services.onboarding_events import log_onboarding_event
from services.api.app.services.profile import save_timezone
from services.api.app.types import SessionProtocol
from sqlalchemy.orm import Session
from services.api.app.diabetes.utils.ui import (
    PHOTO_BUTTON_TEXT,
    build_timezone_webapp_button,
    menu_keyboard,
)
from services.api.app.utils import choose_variant
import services.bot.main as bot_main
from .reminder_jobs import DefaultJobQueue
from . import reminder_handlers

warnings.filterwarnings(
    "ignore",
    message=(
        "If 'per_message=True', all entry points, state handlers, and fallbacks "
        "must be 'CallbackQueryHandler'"
    ),
    category=PTBUserWarning,
)

logger = logging.getLogger(__name__)

# Conversation states
PROFILE, TIMEZONE, REMINDERS = range(3)
ONB_PROFILE_ICR = PROFILE

# Callback identifiers
CB_PROFILE_PREFIX = "onb_prof_"
CB_REMINDER_PREFIX = "onb_rem_"
CB_BACK = "onb_back"
CB_SKIP = "onb_skip"
CB_CANCEL = "onb_cancel"
CB_DONE = "onb_done"


def _progress(step: int) -> str:
    return f"Шаг {step}/3"


VARIANT_ORDER: dict[str | None, list[int]] = {
    "A": [PROFILE, TIMEZONE, REMINDERS],
    "B": [TIMEZONE, PROFILE, REMINDERS],
    None: [PROFILE, TIMEZONE, REMINDERS],
}


def _step_num(step: int, variant: str | None) -> int:
    order = VARIANT_ORDER.get(variant, VARIANT_ORDER[None])
    return order.index(step) + 1


def _next_step(step: int, variant: str | None) -> int | None:
    order = VARIANT_ORDER.get(variant, VARIANT_ORDER[None])
    idx = order.index(step)
    return order[idx + 1] if idx + 1 < len(order) else None


def _prev_step(step: int, variant: str | None) -> int | None:
    order = VARIANT_ORDER.get(variant, VARIANT_ORDER[None])
    idx = order.index(step)
    return order[idx - 1] if idx > 0 else None


def _nav_buttons(
    *, back: bool = False, skip: bool = True
) -> list[InlineKeyboardButton]:
    buttons: list[InlineKeyboardButton] = []
    if back:
        buttons.append(InlineKeyboardButton("Назад", callback_data=CB_BACK))
    if skip:
        buttons.append(InlineKeyboardButton("Пропустить", callback_data=CB_SKIP))
    buttons.append(InlineKeyboardButton("Отмена", callback_data=CB_CANCEL))
    return buttons


def _profile_keyboard(*, back: bool = False) -> InlineKeyboardMarkup:
    options = [
        ("СД2 без инсулина", "t2_no"),
        ("СД2 на инсулине", "t2_ins"),
        ("СД1", "t1"),
        ("ГСД", "gdm"),
        ("Родитель", "parent"),
    ]
    rows = [
        [InlineKeyboardButton(text, callback_data=f"{CB_PROFILE_PREFIX}{code}")]
        for text, code in options
    ]
    rows.append(_nav_buttons(back=back))
    return InlineKeyboardMarkup(rows)


def _timezone_keyboard(*, back: bool = True) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    auto_btn = build_timezone_webapp_button()
    if auto_btn is not None:
        rows.append([auto_btn])
    rows.append(_nav_buttons(back=back))
    return InlineKeyboardMarkup(rows)


def _reminders_keyboard() -> InlineKeyboardMarkup:
    presets = [
        ("Сахар 08:00", "sugar_08"),
        ("Длинный инсулин 22:00", "long_22"),
        ("Таблетки 09:00", "pills_09"),
    ]
    rows = [
        [InlineKeyboardButton(text, callback_data=f"{CB_REMINDER_PREFIX}{code}")]
        for text, code in presets
    ]
    rows.append([InlineKeyboardButton("Готово", callback_data=CB_DONE)])
    rows.append(_nav_buttons(back=True))
    return InlineKeyboardMarkup(rows)


async def _log_event(user_id: int, name: str, step: int, variant: str | None) -> None:
    def _log(session: SessionProtocol) -> None:
        log_onboarding_event(
            cast(Session, session), user_id, name, step=str(step), variant=variant
        )

    try:
        await run_db(_log, sessionmaker=SessionLocal)
    except Exception:  # pragma: no cover - logging only
        logger.exception("Failed to log onboarding event")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for ``/start`` command."""

    message = update.message
    user = update.effective_user
    if message is None or user is None:
        return ConversationHandler.END
    video_url = config.ONBOARDING_VIDEO_URL
    if video_url:
        try:
            await message.reply_video(video_url)
        except Exception:  # pragma: no cover - fallback
            await message.reply_text(video_url)
    user_id = user.id
    await ensure_user_exists(user_id)
    user_data = cast(dict[str, Any], context.user_data)
    args = getattr(context, "args", [])
    variant = args[0] if args else None
    state = await onboarding_state.load_state(user_id)
    if state is not None:
        user_data.update(state.data)
        variant = variant or state.variant
    if variant is None:
        variant = choose_variant(user_id)
    user_data["variant"] = variant
    await _log_event(user_id, "onboarding_started", 0, variant)
    if state is not None:
        if state.step == PROFILE:
            return await _prompt_profile(message, user_id, user_data, variant)
        if state.step == TIMEZONE:
            return await _prompt_timezone(message, user_id, user_data, variant)
        if state.step == REMINDERS:
            return await _prompt_reminders(message, user_id, user_data, variant)
    first_step = VARIANT_ORDER.get(variant, VARIANT_ORDER[None])[0]
    if first_step == TIMEZONE:
        return await _prompt_timezone(message, user_id, user_data, variant)
    return await _prompt_profile(message, user_id, user_data, variant)


async def profile_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle profile selection and navigation from step 1."""

    query = update.callback_query
    user = update.effective_user
    if query is None or query.data is None or query.message is None or user is None:
        return ConversationHandler.END
    message = cast(Message, query.message)
    user_id = user.id
    user_data = cast(dict[str, Any], context.user_data)
    state = await onboarding_state.load_state(user_id)
    variant = cast(str | None, user_data.get("variant"))
    if state is not None:
        user_data.update(state.data)
        variant = variant or state.variant
        user_data["variant"] = variant
        if state.step != PROFILE:
            if state.step == TIMEZONE:
                return await _prompt_timezone(message, user_id, user_data, variant)
            if state.step == REMINDERS:
                return await _prompt_reminders(message, user_id, user_data, variant)
    await query.answer()
    data = query.data
    if data == CB_BACK and _step_num(PROFILE, variant) != 1:
        return await _prompt_timezone(message, user_id, user_data, variant)
    if data == CB_SKIP:
        step_num = _step_num(PROFILE, variant)
        await _log_event(user_id, f"step_completed_{step_num}", step_num, variant)
        next_step = _next_step(PROFILE, variant)
        if next_step == REMINDERS:
            return await _prompt_reminders(message, user_id, user_data, variant)
        return await _prompt_timezone(message, user_id, user_data, variant)
    if data == CB_CANCEL:
        step_num = _step_num(PROFILE, variant)
        await _log_event(user_id, "onboarding_canceled", step_num, variant)
        await message.reply_text("Отменено.")
        return ConversationHandler.END
    if data.startswith(CB_PROFILE_PREFIX):
        user_data["profile"] = data[len(CB_PROFILE_PREFIX) :]
        step_num = _step_num(PROFILE, variant)
        await _log_event(user_id, f"step_completed_{step_num}", step_num, variant)
        next_step = _next_step(PROFILE, variant)
        if next_step == REMINDERS:
            return await _prompt_reminders(message, user_id, user_data, variant)
        return await _prompt_timezone(message, user_id, user_data, variant)
    return ConversationHandler.END


async def _prompt_timezone(
    message: Message, user_id: int, user_data: dict[str, Any], variant: str | None
) -> int:
    await onboarding_state.save_state(user_id, TIMEZONE, user_data, variant)
    step_num = _step_num(TIMEZONE, variant)
    await message.reply_text(
        f"{_progress(step_num)}. Введите часовой пояс (например, Europe/Moscow).",
        reply_markup=_timezone_keyboard(back=step_num != 1),
    )
    return TIMEZONE


async def timezone_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle timezone text input."""

    message = update.message
    user = update.effective_user
    if message is None or message.text is None or user is None:
        return ConversationHandler.END
    user_id = user.id
    user_data = cast(dict[str, Any], context.user_data)
    state = await onboarding_state.load_state(user_id)
    variant = cast(str | None, user_data.get("variant"))
    if state is not None:
        user_data.update(state.data)
        variant = variant or state.variant
        user_data["variant"] = variant
        if state.step != TIMEZONE:
            if state.step == PROFILE:
                return await _prompt_profile(message, user_id, user_data, variant)
            if state.step == REMINDERS:
                return await _prompt_reminders(message, user_id, user_data, variant)
    raw = message.text.strip() or "Europe/Moscow"
    try:
        ZoneInfo(raw)
    except ZoneInfoNotFoundError:
        await message.reply_text(
            "Некорректный часовой пояс. Пример: Europe/Moscow",
            reply_markup=_timezone_keyboard(),
        )
        return TIMEZONE
    user_data["timezone"] = raw
    await onboarding_state.save_state(user_id, TIMEZONE, user_data, variant)
    await save_timezone(user_id, raw, auto=False)
    step_num = _step_num(TIMEZONE, variant)
    await _log_event(user_id, f"step_completed_{step_num}", step_num, variant)
    next_step = _next_step(TIMEZONE, variant)
    if next_step == PROFILE:
        return await _prompt_profile(message, user_id, user_data, variant)
    return await _prompt_reminders(message, user_id, user_data, variant)


async def timezone_webapp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle timezone input coming from WebApp."""

    message = update.effective_message
    user = update.effective_user
    if (
        message is None
        or getattr(message, "web_app_data", None) is None
        or user is None
    ):
        return ConversationHandler.END
    user_id = user.id
    user_data = cast(dict[str, Any], context.user_data)
    state = await onboarding_state.load_state(user_id)
    variant = cast(str | None, user_data.get("variant"))
    if state is not None:
        user_data.update(state.data)
        variant = variant or state.variant
        user_data["variant"] = variant
        if state.step != TIMEZONE:
            if state.step == PROFILE:
                return await _prompt_profile(message, user_id, user_data, variant)
            if state.step == REMINDERS:
                return await _prompt_reminders(message, user_id, user_data, variant)
    web_app = cast(WebAppData, message.web_app_data)
    raw = web_app.data.strip() or "Europe/Moscow"
    try:
        ZoneInfo(raw)
    except ZoneInfoNotFoundError:
        await message.reply_text(
            "Некорректный часовой пояс. Пример: Europe/Moscow",
            reply_markup=_timezone_keyboard(),
        )
        return TIMEZONE
    user_data["timezone"] = raw
    await save_timezone(user_id, raw, auto=True)
    await onboarding_state.save_state(user_id, TIMEZONE, user_data, variant)
    step_num = _step_num(TIMEZONE, variant)
    await _log_event(user_id, f"step_completed_{step_num}", step_num, variant)
    next_step = _next_step(TIMEZONE, variant)
    if next_step == PROFILE:
        return await _prompt_profile(message, user_id, user_data, variant)
    return await _prompt_reminders(message, user_id, user_data, variant)


async def timezone_nav(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle navigation callbacks in timezone step."""

    query = update.callback_query
    user = update.effective_user
    if query is None or query.data is None or query.message is None or user is None:
        return ConversationHandler.END
    message = cast(Message, query.message)
    user_id = user.id
    user_data = cast(dict[str, Any], context.user_data)
    state = await onboarding_state.load_state(user_id)
    variant = cast(str | None, user_data.get("variant"))
    if state is not None:
        user_data.update(state.data)
        variant = variant or state.variant
        user_data["variant"] = variant
        if state.step != TIMEZONE:
            if state.step == PROFILE:
                return await _prompt_profile(message, user_id, user_data, variant)
            if state.step == REMINDERS:
                return await _prompt_reminders(message, user_id, user_data, variant)
    await query.answer()
    data = query.data
    step_num = _step_num(TIMEZONE, variant)
    if data == CB_BACK and step_num != 1:
        return await _prompt_profile(message, user_id, user_data, variant)
    if data == CB_SKIP:
        await _log_event(user_id, f"step_completed_{step_num}", step_num, variant)
        next_step = _next_step(TIMEZONE, variant)
        if next_step == PROFILE:
            return await _prompt_profile(message, user_id, user_data, variant)
        return await _prompt_reminders(message, user_id, user_data, variant)
    if data == CB_CANCEL:
        await _log_event(user_id, "onboarding_canceled", step_num, variant)
        await message.reply_text("Отменено.")
        return ConversationHandler.END
    return TIMEZONE


async def _prompt_profile(
    message: Message, user_id: int, user_data: dict[str, Any], variant: str | None
) -> int:
    await onboarding_state.save_state(user_id, PROFILE, user_data, variant)
    step_num = _step_num(PROFILE, variant)
    await message.reply_text(
        f"{_progress(step_num)}. Выберите профиль:",
        reply_markup=_profile_keyboard(back=step_num != 1),
    )
    return PROFILE


async def _prompt_reminders(
    message: Message, user_id: int, user_data: dict[str, Any], variant: str | None
) -> int:
    await onboarding_state.save_state(user_id, REMINDERS, user_data, variant)
    step_num = _step_num(REMINDERS, variant)
    await message.reply_text(
        f"{_progress(step_num)}. Выберите напоминания:",
        reply_markup=_reminders_keyboard(),
    )
    return REMINDERS


async def reminders_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle reminder preset selection and navigation."""

    query = update.callback_query
    user = update.effective_user
    if query is None or query.data is None or query.message is None or user is None:
        return ConversationHandler.END
    message = cast(Message, query.message)
    user_id = user.id
    user_data = cast(dict[str, Any], context.user_data)
    state = await onboarding_state.load_state(user_id)
    variant = cast(str | None, user_data.get("variant"))
    if state is not None:
        user_data.update(state.data)
        variant = variant or state.variant
        user_data["variant"] = variant
        if state.step != REMINDERS:
            if state.step == PROFILE:
                return await _prompt_profile(message, user_id, user_data, variant)
            if state.step == TIMEZONE:
                return await _prompt_timezone(message, user_id, user_data, variant)
    await query.answer()
    data = query.data
    if data == CB_BACK:
        prev_step = _prev_step(REMINDERS, variant)
        if prev_step == PROFILE:
            return await _prompt_profile(message, user_id, user_data, variant)
        return await _prompt_timezone(message, user_id, user_data, variant)
    if data in {CB_SKIP, CB_DONE}:
        save_data = dict(user_data)
        if "reminders" in save_data:
            save_data["reminders"] = list(cast(Iterable[str], save_data["reminders"]))
        await onboarding_state.save_state(user_id, REMINDERS, save_data, variant)
        return await _finish(
            message,
            user_id,
            user_data,
            cast("DefaultJobQueue | None", context.job_queue),
        )
    if data == CB_CANCEL:
        await _log_event(user_id, "onboarding_canceled", 3, variant)
        await message.reply_text("Отменено.")
        return ConversationHandler.END
    if data.startswith(CB_REMINDER_PREFIX):
        reminders = cast(list[str], user_data.setdefault("reminders", []))
        code = data[len(CB_REMINDER_PREFIX) :]
        if code in reminders:
            reminders.remove(code)
        else:
            reminders.append(code)
        await onboarding_state.save_state(
            user_id,
            REMINDERS,
            {**user_data, "reminders": list(reminders)},
            variant,
        )
        return REMINDERS
    save_data = dict(user_data)
    if "reminders" in save_data:
        save_data["reminders"] = list(cast(Iterable[str], save_data["reminders"]))
    await onboarding_state.save_state(user_id, REMINDERS, save_data, variant)
    return REMINDERS


async def onboarding_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip onboarding and show final message."""

    query = update.callback_query
    user = update.effective_user
    if query is None or query.message is None or user is None:
        return ConversationHandler.END
    message = cast(Message, query.message)
    await query.answer()
    user_data = cast(dict[str, Any], getattr(context, "user_data", {}))
    variant = cast(str | None, user_data.get("variant"))
    await onboarding_state.complete_state(user.id)
    await _mark_user_complete(user.id)
    await _log_event(user.id, "onboarding_finished", 3, variant)
    await message.reply_text("Пропущено", reply_markup=menu_keyboard())
    bot = cast(ExtBot[None], message.get_bot())
    try:
        await bot.set_my_commands(bot_main.commands)
    except Exception as e:  # pragma: no cover - network errors
        logger.warning("set_my_commands failed: %s", e)
    return ConversationHandler.END


async def onboarding_reminders(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Finish onboarding when reminders step is skipped."""

    query = update.callback_query
    user = update.effective_user
    if query is None or query.message is None or user is None:
        return ConversationHandler.END
    await query.answer()
    message = cast(Message, query.message)
    user_data = cast(dict[str, Any], getattr(context, "user_data", {}))
    variant = cast(str | None, user_data.get("variant"))
    save_data = dict(user_data)
    if "reminders" in save_data:
        save_data["reminders"] = list(cast(Iterable[str], save_data["reminders"]))
    await onboarding_state.save_state(user.id, REMINDERS, save_data, variant)
    return await _finish(
        message,
        user.id,
        user_data,
        cast("DefaultJobQueue | None", context.job_queue),
    )


async def _finish(
    message: Message,
    user_id: int,
    user_data: dict[str, Any],
    job_queue: DefaultJobQueue | None,
) -> int:
    variant = cast(str | None, user_data.get("variant"))
    await onboarding_state.complete_state(user_id)
    await _mark_user_complete(user_id)
    reminders = []
    for code in cast(list[str], user_data.get("reminders", [])):
        rem = await reminder_handlers.create_reminder_from_preset(
            user_id, code, job_queue
        )
        if rem is not None:
            action = getattr(
                rem, "title", None
            ) or reminder_handlers.REMINDER_ACTIONS.get(rem.type, rem.type)
            if action.startswith("Замерить "):
                action = action.split(" ", 1)[1]
            time_val = getattr(rem, "time", None)
            if isinstance(time_val, time_cls):
                time_str = time_val.strftime("%H:%M")
            else:
                time_str = str(time_val) if time_val is not None else ""
            reminders.append(f"{action.capitalize()} {time_str}".strip())
    if reminders:
        await message.reply_text("Созданы напоминания:\n" + "\n".join(reminders))
    await _log_event(user_id, "step_completed_3", 3, variant)
    await message.reply_text(
        "🎉 Готово! Настройка завершена.", reply_markup=menu_keyboard()
    )
    await _log_event(user_id, "onboarding_finished", 3, variant)
    bot = cast(ExtBot[None], message.get_bot())
    try:
        await bot.set_my_commands(bot_main.commands)
    except Exception as e:  # pragma: no cover - network errors
        logger.warning("set_my_commands failed: %s", e)
    return ConversationHandler.END


async def onboarding_poll_answer(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Stub for backward compatibility."""

    return None


async def _photo_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle accidental photo messages during onboarding."""

    message = update.message
    user = update.effective_user
    if message is not None:
        await message.reply_text("Отменено.")
        await message.reply_text("Загрузите фото позже через соответствующую команду.")
    user_data = cast(dict[str, Any], context.user_data)
    variant = cast(str | None, user_data.get("variant"))
    if user is not None:
        await _log_event(user.id, "onboarding_canceled", 0, variant)
    user_data.clear()
    return ConversationHandler.END


async def _mark_user_complete(user_id: int) -> None:
    def _update(session: SessionProtocol) -> None:
        user = cast(User | None, session.get(User, user_id))
        if user is None:
            return
        user.onboarding_complete = True
        commit(cast(Session, session))

    await run_db(_update, sessionmaker=SessionLocal)


async def reset_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Reset onboarding progress and allow user to restart."""

    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return ConversationHandler.END

    store = cast(
        OnboardingStateStore,
        context.application.bot_data.setdefault("onb_state", OnboardingStateStore()),
    )
    store.reset(user.id)

    def _reset(session: SessionProtocol) -> None:
        state = cast(
            onboarding_state.OnboardingState | None,
            session.get(onboarding_state.OnboardingState, user.id),
        )
        if state is not None:
            session.delete(state)
        db_user = cast(User | None, session.get(User, user.id))
        if db_user is not None:
            db_user.onboarding_complete = False
        commit(cast(Session, session))

    await run_db(_reset, sessionmaker=SessionLocal)
    await message.reply_text(
        "Онбординг сброшен. Отправьте /start, чтобы начать заново."
    )
    return ConversationHandler.END


onboarding_conv = ConversationHandler(
    entry_points=[
        CommandHandler("start", start_command),
        CommandHandler("reset_onboarding", reset_onboarding),
    ],
    states={
        PROFILE: [CallbackQueryHandler(profile_chosen)],
        TIMEZONE: [
            CallbackQueryHandler(
                timezone_nav,
                pattern=f"^({CB_BACK}|{CB_SKIP}|{CB_CANCEL})$",
            ),
            MessageHandler(filters.StatusUpdate.WEB_APP_DATA, timezone_webapp),
            MessageHandler(filters.TEXT & (~filters.COMMAND), timezone_text),
        ],
        REMINDERS: [CallbackQueryHandler(reminders_chosen)],
    },
    fallbacks=[
        MessageHandler(filters.Regex(f"^{PHOTO_BUTTON_TEXT}$"), _photo_fallback)
    ],
)
__all__ = [
    "PROFILE",
    "TIMEZONE",
    "REMINDERS",
    "ONB_PROFILE_ICR",
    "start_command",
    "profile_chosen",
    "timezone_webapp",
    "timezone_text",
    "timezone_nav",
    "reminders_chosen",
    "reset_onboarding",
    "onboarding_skip",
    "onboarding_reminders",
    "onboarding_poll_answer",
    "onboarding_conv",
]
