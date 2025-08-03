"""Handlers related to patient profile management."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from diabetes.db import SessionLocal, Profile
from diabetes.ui import menu_keyboard
from .common_handlers import commit_session

PROFILE_ICR, PROFILE_CF, PROFILE_TARGET = range(0, 3)


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
        commit_session(session)

    await update.message.reply_text(
        f"✅ Профиль обновлён:\n"
        f"• ИКХ: {icr} г/ед.\n"
        f"• КЧ: {cf} ммоль/л\n"
        f"• Целевой сахар: {target} ммоль/л" + warning_msg,
        parse_mode="Markdown",
    )


async def profile_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display current patient profile."""
    context.user_data.clear()
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
        f"• ИКХ: {profile.icr} г/ед.\n"
        f"• КЧ: {profile.cf} ммоль/л\n"
        f"• Целевой сахар: {profile.target_bg} ммоль/л"
    )
    await update.message.reply_text(msg)


async def profile_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel profile creation conversation."""
    await update.message.reply_text("Отменено.", reply_markup=menu_keyboard)
    return ConversationHandler.END


__all__ = [
    "PROFILE_ICR",
    "PROFILE_CF",
    "PROFILE_TARGET",
    "profile_command",
    "profile_view",
    "profile_cancel",
]
