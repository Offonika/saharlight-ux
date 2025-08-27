"""Onboarding wizard handlers for /start command.

Implements a three-step conversation:

1. Profile form (ICR, CF, target).
2. Demo photo with example command.
3. Suggest enabling reminders.

After completion a small emoji poll is sent (👍🙂👎) and the result is
logged.  The wizard is executed only once per user; subsequent ``/start``
invocations show the greeting and menu without triggering the wizard.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from services.api.app.diabetes.handlers.callbackquery_no_warn_handler import CallbackQueryNoWarnHandler

from services.api.app.diabetes.services.db import SessionLocal, User, Profile, Reminder
from services.api.app.diabetes.utils.ui import menu_keyboard, build_timezone_webapp_button
from services.api.app.diabetes.services.repository import commit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from openai import OpenAIError


logger = logging.getLogger(__name__)

DEMO_PHOTO_PATH = (
    Path(__file__).resolve().parents[5] / "docs" / "assets" / "demo.jpg"
)


# Wizard states
ONB_PROFILE_ICR, ONB_PROFILE_CF, ONB_PROFILE_TARGET, ONB_PROFILE_TZ, ONB_DEMO, ONB_REMINDERS = range(6)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for ``/start``.

    For first-time users runs the onboarding wizard.  For users who have
    already completed onboarding simply shows the greeting and menu.
    """

    context.user_data: dict[str, Any] = context.user_data or {}
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name or ""

    with SessionLocal() as session:
        user = session.get(User, user_id)
        if not user:
            from services.api.app.diabetes.services.gpt_client import create_thread

            try:
                thread_id = create_thread()
            except OpenAIError as exc:  # pragma: no cover - network errors
                logger.exception("Failed to create thread for user %s: %s", user_id, exc)
                await update.message.reply_text(
                    "⚠️ Не удалось инициализировать профиль. Попробуйте позже."
                )
                return ConversationHandler.END
            user = User(telegram_id=user_id, thread_id=thread_id)
            session.add(user)
            if not commit(session):
                await update.message.reply_text(
                    "⚠️ Не удалось сохранить профиль пользователя."
                )
                return ConversationHandler.END

        if user.onboarding_complete:
            greeting = (
                f"👋 Привет, {first_name}!" if first_name else "👋 Привет!"
            )
            greeting += (
                " Рада видеть тебя. Надеюсь, у тебя сегодня всё отлично."
            )
            await update.message.reply_text(
                f"{greeting}\n\n📋 Выберите действие:", reply_markup=menu_keyboard
            )
            return ConversationHandler.END

    await update.message.reply_text(
        "👋 Привет! Давай начнём.\n1/3. Введите коэффициент ИКХ (г/ед.):",
        reply_markup=_skip_markup(),
    )
    return ONB_PROFILE_ICR


def _skip_markup() -> InlineKeyboardMarkup:
    """Markup containing a single *skip* button."""

    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Пропустить", callback_data="onb_skip")]]
    )


async def onboarding_icr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle ICR input."""
    context.user_data: dict[str, Any] = context.user_data or {}
    try:
        icr = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text(
            "Введите ИКХ числом.", reply_markup=_skip_markup()
        )
        return ONB_PROFILE_ICR
    if icr <= 0:
        await update.message.reply_text(
            "ИКХ должен быть больше 0.", reply_markup=_skip_markup()
        )
        return ONB_PROFILE_ICR
    context.user_data["profile_icr"] = icr
    await update.message.reply_text(
        "2/3. Введите коэффициент чувствительности (КЧ) ммоль/л.",
        reply_markup=_skip_markup(),
    )
    return ONB_PROFILE_CF


async def onboarding_cf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle CF input."""
    context.user_data: dict[str, Any] = context.user_data or {}
    try:
        cf = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text(
            "Введите КЧ числом.", reply_markup=_skip_markup()
        )
        return ONB_PROFILE_CF
    if cf <= 0:
        await update.message.reply_text(
            "КЧ должен быть больше 0.", reply_markup=_skip_markup()
        )
        return ONB_PROFILE_CF
    context.user_data["profile_cf"] = cf
    await update.message.reply_text(
        "3/3. Введите целевой уровень сахара (ммоль/л).",
        reply_markup=_skip_markup(),
    )
    return ONB_PROFILE_TARGET


async def onboarding_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle target BG input and proceed to demo."""
    context.user_data: dict[str, Any] = context.user_data or {}
    try:
        target = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text(
            "Введите целевой сахар числом.", reply_markup=_skip_markup()
        )
        return ONB_PROFILE_TARGET
    if target <= 0:
        await update.message.reply_text(
            "Целевой сахар должен быть больше 0.", reply_markup=_skip_markup()
        )
        return ONB_PROFILE_TARGET

    icr = context.user_data.pop("profile_icr", None)
    cf = context.user_data.pop("profile_cf", None)
    if icr is None or cf is None:
        await update.message.reply_text(
            "⚠️ Не хватает данных для профиля. Пожалуйста, начните заново."
        )
        return ConversationHandler.END
    user_id = update.effective_user.id

    with SessionLocal() as session:
        prof = session.get(Profile, user_id)
        if not prof:
            prof = Profile(telegram_id=user_id)
            session.add(prof)
        prof.icr = icr
        prof.cf = cf
        prof.target_bg = target
        if not commit(session):
            await update.message.reply_text("⚠️ Не удалось сохранить профиль.")
            return ConversationHandler.END

    keyboard_buttons = []
    tz_button = build_timezone_webapp_button()
    if tz_button:
        keyboard_buttons.append(tz_button)
    keyboard_buttons.append(InlineKeyboardButton("Пропустить", callback_data="onb_skip"))
    await update.message.reply_text(
        "Введите ваш часовой пояс (например Europe/Moscow) или используйте кнопку ниже:",
        reply_markup=InlineKeyboardMarkup([keyboard_buttons]),
    )
    return ONB_PROFILE_TZ


async def onboarding_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user timezone (text or WebApp) and proceed to demo."""
    context.user_data: dict[str, Any] = context.user_data or {}
    if getattr(update.message, "web_app_data", None):
        tz_name = update.message.web_app_data.data
    else:
        tz_name = update.message.text.strip()
    buttons: list[InlineKeyboardButton] = []
    tz_button = build_timezone_webapp_button()
    if tz_button:
        buttons.append(tz_button)
    buttons.append(InlineKeyboardButton("Пропустить", callback_data="onb_skip"))
    try:
        ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:

        logger.warning("Invalid timezone provided by user %s: %s", update.effective_user.id, tz_name)
        buttons = []
        tz_button = build_timezone_webapp_button()
        if tz_button:
            buttons.append(tz_button)
        buttons.append(InlineKeyboardButton("Пропустить", callback_data="onb_skip"))

        await update.message.reply_text(
            "Введите корректный часовой пояс, например Europe/Moscow.",
            reply_markup=InlineKeyboardMarkup([buttons]),
        )
        return ONB_PROFILE_TZ
    except Exception:  # pragma: no cover - unexpected errors
        logger.exception("Unexpected error validating timezone %s", tz_name)
        await update.message.reply_text(
            "⚠️ Произошла ошибка при проверке часового пояса.",
            reply_markup=InlineKeyboardMarkup([buttons]),
        )
        return ONB_PROFILE_TZ
    user_id = update.effective_user.id
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if user:
            user.timezone = tz_name
            if not commit(session):
                await update.message.reply_text(

                    "⚠️ Не удалось сохранить часовой пояс."

                )
                return ConversationHandler.END

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Далее", callback_data="onb_next")]]
    )
    try:
        with DEMO_PHOTO_PATH.open("rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption="2/3. Вот пример распознавания еды.",
                reply_markup=keyboard,
            )
    except OSError:
        logger.exception("Failed to open demo photo")
        await update.message.reply_text(
            "2/3. Демо-фото недоступно.",
            reply_markup=keyboard,
        )
    return ONB_DEMO


async def onboarding_demo_next(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Proceed from demo to reminder suggestion."""
    context.user_data: dict[str, Any] = context.user_data or {}
    query = update.callback_query
    await query.answer()
    await query.message.delete()

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Да", callback_data="onb_rem_yes"),
                InlineKeyboardButton("Нет", callback_data="onb_rem_no"),
            ]
        ]
    )
    await query.message.reply_text(
        "3/3. Включить напоминания о замерах сахара?",
        reply_markup=keyboard,
    )
    return ONB_REMINDERS


async def onboarding_reminders(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle reminder choice and finish onboarding."""
    context.user_data: dict[str, Any] = context.user_data or {}
    query = update.callback_query
    await query.answer()
    enable = query.data == "onb_rem_yes"
    user_id = update.effective_user.id
    reminders: list[Reminder] = []
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if user:
            user.onboarding_complete = True
            if enable:
                reminders = (
                    session.query(Reminder)
                    .filter_by(telegram_id=user_id, type="sugar")
                    .all()
                )
                if not reminders:
                    reminders = [
                        Reminder(
                            telegram_id=user_id,
                            type="sugar",
                            interval_hours=4,
                        )
                    ]
                    session.add_all(reminders)
                else:
                    for rem in reminders:
                        rem.is_enabled = True
            else:
                reminders = (
                    session.query(Reminder)
                    .filter_by(telegram_id=user_id, type="sugar")
                    .all()
                )
                for rem in reminders:
                    rem.is_enabled = False
            if not commit(session):
                await query.message.reply_text(
                    "⚠️ Не удалось сохранить настройки."
                )
                return ConversationHandler.END

    if getattr(context, "job_queue", None):
        if enable:
            from . import reminder_handlers

            for rem in reminders:
                reminder_handlers.schedule_reminder(rem, context.job_queue)
        else:
            for rem in reminders:
                for job in context.job_queue.get_jobs_by_name(
                    f"reminder_{rem.id}"
                ):
                    job.schedule_removal()
    else:
        logger.warning("Job queue not available, skipping reminder scheduling")

    logger.info("User %s reminder choice: %s", user_id, enable)

    poll_msg = await query.message.reply_poll(
        "Как вам онбординг?",
        ["👍", "🙂", "👎"],
        is_anonymous=False,
    )
    polls: dict[str, int] = context.bot_data.setdefault("onboarding_polls", {})
    polls[poll_msg.poll.id] = user_id

    await query.message.reply_text(
        "Готово! Спасибо за настройку.", reply_markup=menu_keyboard
    )
    return ConversationHandler.END


async def onboarding_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip the onboarding entirely."""
    context.user_data: dict[str, Any] = context.user_data or {}
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    with SessionLocal() as session:
        user = session.get(User, user_id)
        if user:
            user.onboarding_complete = True
            if not commit(session):
                await query.message.reply_text(

                    "⚠️ Не удалось сохранить настройки.",
                    reply_markup=menu_keyboard,

                )
                return ConversationHandler.END

    poll_msg = await query.message.reply_poll(
        "Как вам онбординг?",
        ["👍", "🙂", "👎"],
        is_anonymous=False,
    )
    context.bot_data.setdefault("onboarding_polls", {})[poll_msg.poll.id] = user_id

    await query.message.reply_text(
        "Пропущено.", reply_markup=menu_keyboard
    )
    return ConversationHandler.END


async def onboarding_poll_answer(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Log poll answers from onboarding feedback."""
    context.user_data: dict[str, Any] = context.user_data or {}
    poll_id = update.poll_answer.poll_id
    option_ids = update.poll_answer.option_ids
    user_id = context.bot_data.get("onboarding_polls", {}).pop(poll_id, None)
    if user_id is None or not option_ids:
        return
    option = ["👍", "🙂", "👎"][option_ids[0]]
    logger.info("Onboarding poll result from %s: %s", user_id, option)


async def _photo_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from .dose_handlers import _cancel_then, photo_prompt

    context.user_data: dict[str, Any] = context.user_data or {}
    handler = _cancel_then(photo_prompt)
    return await handler(update, context)


onboarding_conv = ConversationHandler(
    entry_points=[CommandHandler("start", start_command)],
    states={
        ONB_PROFILE_ICR: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_icr),
            CallbackQueryNoWarnHandler(onboarding_skip, pattern="^onb_skip$"),
        ],
        ONB_PROFILE_CF: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_cf),
            CallbackQueryNoWarnHandler(onboarding_skip, pattern="^onb_skip$"),
        ],
        ONB_PROFILE_TARGET: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, onboarding_target),
            CallbackQueryNoWarnHandler(onboarding_skip, pattern="^onb_skip$"),
        ],
        ONB_PROFILE_TZ: [
            MessageHandler(
                (filters.TEXT & ~filters.COMMAND) | filters.StatusUpdate.WEB_APP_DATA,
                onboarding_timezone,
            ),
            CallbackQueryNoWarnHandler(onboarding_skip, pattern="^onb_skip$"),
        ],
        ONB_DEMO: [
            CallbackQueryNoWarnHandler(onboarding_demo_next, pattern="^onb_next$"),
            CallbackQueryNoWarnHandler(onboarding_skip, pattern="^onb_skip$"),
        ],
        ONB_REMINDERS: [
            CallbackQueryNoWarnHandler(onboarding_reminders, pattern="^onb_rem_(yes|no)$"),
            CallbackQueryNoWarnHandler(onboarding_skip, pattern="^onb_skip$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", onboarding_skip),
        MessageHandler(filters.Regex("^📷 Фото еды$"), _photo_fallback),
    ],
    per_message=False,
)


__all__ = [
    "start_command",
    "onboarding_conv",
    "onboarding_poll_answer",
    "ONB_PROFILE_ICR",
    "ONB_PROFILE_CF",
    "ONB_PROFILE_TARGET",
    "ONB_PROFILE_TZ",
    "ONB_DEMO",
    "ONB_REMINDERS",
]
