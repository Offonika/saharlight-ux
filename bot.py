from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import TELEGRAM_TOKEN
from db import init_db
from bot.startup import setup
from bot.conversations import (
    onboarding_conv,
    sugar_conv,
    photo_conv,
    dose_conv,
    profile_conv,
)
from bot.handlers import (
    start,
    menu_handler,
    reset_handler,
    history_handler,
    profile_command,
    profile_view,
    sugar_start,
    photo_request,
    report_handler,
    callback_router,
    freeform_handler,
    help_handler,
)


logger = setup()


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a notification to the user."""
    logger.error("Exception while handling an update:", exc_info=context.error)

    if update and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Произошла непредвиденная ошибка. Попробуйте еще раз позже.",
            )
        except Exception:  # pragma: no cover - best effort to notify
            logger.exception("Failed to send error message to user")


async def post_init(application: Application) -> None:
    """Configure bot commands after the application is initialized."""
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Запустить бота"),
            BotCommand("menu", "Главное меню"),
            BotCommand("reset", "Сбросить разговор"),
            BotCommand("history", "История сахара"),
            BotCommand("profile", "Профиль"),
            BotCommand("report", "Отчёт"),
            BotCommand("help", "Помощь"),
        ]
    )

def main() -> None:
    init_db()
    application = (
        ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    )
    application.add_error_handler(error_handler)
    application.add_handler(onboarding_conv)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu_handler))
    application.add_handler(CommandHandler("reset", reset_handler))
    application.add_handler(CommandHandler("history", history_handler))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(MessageHandler(filters.Regex("^📄 Мой профиль$"), profile_view))
    application.add_handler(MessageHandler(filters.Regex(r"^📊 История$"), history_handler))
    application.add_handler(MessageHandler(filters.Regex(r"^❓ Мой сахар$"), sugar_start))
    application.add_handler(sugar_conv)
    application.add_handler(photo_conv)
    application.add_handler(profile_conv)
    application.add_handler(dose_conv)
    application.add_handler(MessageHandler(filters.Regex(r"^📷 Фото еды$"), photo_request))
    application.add_handler(CommandHandler("report", report_handler))
    application.add_handler(MessageHandler(filters.Regex("^📈 Отчёт$"), report_handler))
    application.add_handler(CallbackQueryHandler(callback_router))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, freeform_handler))
    application.add_handler(CommandHandler("help", help_handler))

    application.run_polling()


if __name__ == "__main__":
    main()
