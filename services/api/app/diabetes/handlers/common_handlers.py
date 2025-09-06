"""Common utility handlers."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from services.api.app.diabetes.utils.ui import menu_keyboard
from .learning_handlers import learn_command


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the main menu keyboard using ``menu_keyboard``."""
    message = update.message
    if message:
        await message.reply_text("📋 Выберите действие:", reply_markup=menu_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show available commands, including :command:`/menu`, and menu buttons."""

    text = (
        "📚 Доступные команды:\n"
        "/start - запустить бота\n"
        "/menu - главное меню (вернуться к кнопкам)\n"
        "/profile - мой профиль\n"
        "/report - отчёт\n"
        "/sugar - уровень сахара\n"
        "/gpt - чат с GPT\n"
        "/topics - список тем\n"
        "/reminders - список напоминаний\n"
        "/cancel - отменить ввод\n"
        "/help - справка\n"
        "/soscontact — настроить контакт для SOS-уведомлений\n"
        "/hypoalert - FAQ по гипогликемии\n\n"
        "🆕 Новые возможности:\n"
        "• ✨ Мастер настройки при первом запуске\n"
        "• 🕹 Быстрый ввод (smart-input)\n"
        "• ✏️ Редактирование записей\n\n"
        "🔔 Безопасность:\n"
        "• Пороги низкого и высокого сахара\n"
        "• SOS-уведомления\n"
        "• Напоминания (команда /reminders)\n"
        "• FAQ по гипогликемии: /hypoalert\n"
        "Настройки: /profile → «🔔 Безопасность»\n\n"
        "Напоминания (команда /reminders):\n"
        "• Сахар — напомнит измерить уровень сахара\n"
        "• Длинный инсулин — напомнит о базальном уколе\n"
        "• Лекарство — принять таблетки\n"
        "• Проверить ХЕ после еды — через N минут после записи\n"
        "Время вводите как ЧЧ:ММ, интервал — число часов, после еды — минуты\n"
        "Для отмены используйте /cancel\n\n"
        "📲 Кнопки меню:\n"
        "🕹 Быстрый ввод\n"
        "📷 Фото еды\n"
        "🩸 Уровень сахара\n"
        "💉 Доза инсулина\n"
        "📈 Отчёт\n"
        "ℹ️ Помощь"
    )
    message = update.message
    if message:
        await message.reply_text(text, reply_markup=menu_keyboard())


async def smart_input_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Explain the smart-input syntax for quick diary entries."""

    text = (
        "🕹 Быстрый ввод позволяет записать сахар, ХЕ и дозу в одном сообщении.\n"
        "Используйте формат: `сахар=<ммоль/л> xe=<ХЕ> dose=<ед>` или свободный текст,\n"
        "например: `5 ммоль/л 3хе 2ед`. Можно указывать только нужные значения."
    )
    message = update.message
    if message:
        await message.reply_text(text, parse_mode="Markdown")


__all__ = [
    "menu_keyboard",
    "menu_command",
    "help_command",
    "smart_input_help",
    "learn_command",
]
