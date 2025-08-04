"""Handlers related to patient profile management."""

from __future__ import annotations

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from diabetes.db import SessionLocal, Profile
from diabetes.ui import menu_keyboard
from .common_handlers import commit_session


PROFILE_ICR, PROFILE_CF, PROFILE_TARGET = range(3)


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set patient profile coefficients via ``/profile`` command."""
    args = context.args
    if len(args) != 3:
        await update.message.reply_text(
            "❗ Формат команды:\n"
            "/profile <ИКХ г/ед.> <КЧ ммоль/л> <целевой>\n"
            "Пример: /profile 10 2 6",
            parse_mode="Markdown",
        )
        return

    try:
        icr = float(args[0].replace(",", "."))
        cf = float(args[1].replace(",", "."))
        target = float(args[2].replace(",", "."))
    except ValueError:
        await update.message.reply_text(
            "❗ Пожалуйста, введите корректные числа. Пример:\n/profile 10 2 6",
            parse_mode="Markdown",
        )
        return

    if icr <= 0 or cf <= 0 or target <= 0:
        await update.message.reply_text(
            "❗ Все значения должны быть больше 0. Пример:\n/profile 10 2 6",
            parse_mode="Markdown",
        )
        return

    warning_msg = ""
    if icr > 8 or cf < 3:
        warning_msg = (
            "\n⚠️ Проверьте, пожалуйста: возможно, вы перепутали местами ИКХ и КЧ.\n"
            f"• Вы ввели ИКХ = {icr} г/ед. (высоковато)\n"
            f"• КЧ = {cf} ммоль/л (низковато)\n\n"
            "Если вы хотели ввести наоборот, отправьте:\n"
            f"/profile {cf} {icr} {target}\n"
        )

    user_id = update.effective_user.id
    with SessionLocal() as session:
        prof = session.get(Profile, user_id)
        if not prof:
            prof = Profile(telegram_id=user_id)
            session.add(prof)

        prof.icr = icr
        prof.cf = cf
        prof.target_bg = target
        if not commit_session(session):
            await update.message.reply_text("⚠️ Не удалось сохранить профиль.")
            return

    await update.message.reply_text(
        f"✅ Профиль обновлён:\n"
        f"• ИКХ: {icr} г/ед.\n"
        f"• КЧ: {cf} ммоль/л\n"
        f"• Целевой сахар: {target} ммоль/л" + warning_msg,
        parse_mode="Markdown",
    )


async def profile_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display current patient profile."""
    user_id = update.effective_user.id
    with SessionLocal() as session:
        profile = session.get(Profile, user_id)

    if not profile:
        await update.message.reply_text(
            "Ваш профиль пока не настроен.\n\n"
            "Чтобы настроить профиль, введите команду:\n"
            "/profile <ИКХ г/ед.> <КЧ ммоль/л> <целевой>\n"
            "Пример: /profile 10 2 6",
            parse_mode="Markdown",
        )
        return

    msg = (
        "📄 Ваш профиль:\n"
        f"• ИКХ: {profile.icr} г/ед.\n"  # Инсулин-карб коэффициент
        f"• КЧ: {profile.cf} ммоль/л\n"
        f"• Целевой сахар: {profile.target_bg} ммоль/л"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✏️ Изменить", callback_data="profile_edit")],
            [InlineKeyboardButton("🔙 Назад", callback_data="profile_back")],
        ]
    )
    await update.message.reply_text(msg, reply_markup=keyboard)


async def profile_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel profile creation conversation."""
    await update.message.reply_text("Отменено.", reply_markup=menu_keyboard)
    return ConversationHandler.END


async def profile_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return to main menu from profile view."""
    query = update.callback_query
    await query.answer()
    await query.message.delete()
    await query.message.reply_text("📋 Выберите действие:", reply_markup=menu_keyboard)


async def profile_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start step-by-step profile setup."""
    query = update.callback_query
    await query.answer()
    await query.message.edit_text("Введите коэффициент ИКХ (г/ед.):")
    return PROFILE_ICR


async def profile_icr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle ICR input."""
    text = update.message.text.strip().replace(",", ".")
    try:
        icr = float(text)
    except ValueError:
        await update.message.reply_text("Введите ИКХ числом.")
        return PROFILE_ICR
    if icr <= 0:
        await update.message.reply_text("ИКХ должен быть больше 0.")
        return PROFILE_ICR
    context.user_data["profile_icr"] = icr
    await update.message.reply_text("Введите коэффициент чувствительности (КЧ) ммоль/л.")
    return PROFILE_CF


async def profile_cf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle CF input."""
    text = update.message.text.strip().replace(",", ".")
    try:
        cf = float(text)
    except ValueError:
        await update.message.reply_text("Введите КЧ числом.")
        return PROFILE_CF
    if cf <= 0:
        await update.message.reply_text("КЧ должен быть больше 0.")
        return PROFILE_CF
    context.user_data["profile_cf"] = cf
    await update.message.reply_text("Введите целевой уровень сахара (ммоль/л).")
    return PROFILE_TARGET


async def profile_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle target BG input and save profile."""
    text = update.message.text.strip().replace(",", ".")
    try:
        target = float(text)
    except ValueError:
        await update.message.reply_text("Введите целевой сахар числом.")
        return PROFILE_TARGET
    if target <= 0:
        await update.message.reply_text("Целевой сахар должен быть больше 0.")
        return PROFILE_TARGET
    icr = context.user_data.pop("profile_icr")
    cf = context.user_data.pop("profile_cf")
    user_id = update.effective_user.id
    with SessionLocal() as session:
        prof = session.get(Profile, user_id)
        if not prof:
            prof = Profile(telegram_id=user_id)
            session.add(prof)
        prof.icr = icr
        prof.cf = cf
        prof.target_bg = target
        if not commit_session(session):
            await update.message.reply_text("⚠️ Не удалось сохранить профиль.")
            return ConversationHandler.END
    await update.message.reply_text(
        "✅ Профиль обновлён:\n"
        f"• ИКХ: {icr} г/ед.\n"
        f"• КЧ: {cf} ммоль/л\n"
        f"• Целевой сахар: {target} ммоль/л",
        reply_markup=menu_keyboard,
    )
    return ConversationHandler.END


profile_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(profile_edit, pattern="^profile_edit$")],
    states={
        PROFILE_ICR: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_icr)],
        PROFILE_CF: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_cf)],
        PROFILE_TARGET: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, profile_target)
        ],
    },
    fallbacks=[CommandHandler("cancel", profile_cancel)],
)


__all__ = [
    "profile_command",
    "profile_view",
    "profile_cancel",
    "profile_back",
    "profile_edit",
    "profile_conv",
]
