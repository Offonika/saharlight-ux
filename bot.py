import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters

from config import TELEGRAM_TOKEN
from db import init_db
from handlers import (
    onboarding_conv,
    sugar_conv,
    photo_conv,
    dose_conv,
    profile_conv,
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


logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger("bot")


def main() -> None:
    init_db()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(onboarding_conv)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_handler))
    app.add_handler(CommandHandler("reset", reset_handler))
    app.add_handler(CommandHandler("history", history_handler))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(MessageHandler(filters.Regex("^📄 Мой профиль$"), profile_view))
    app.add_handler(MessageHandler(filters.Regex(r"^📊 История$"), history_handler))
    app.add_handler(MessageHandler(filters.Regex(r"^❓ Мой сахар$"), sugar_start))
    app.add_handler(sugar_conv)
    app.add_handler(photo_conv)
    app.add_handler(profile_conv)
    app.add_handler(dose_conv)
    app.add_handler(MessageHandler(filters.Regex(r"^📷 Фото еды$"), photo_request))
    app.add_handler(CommandHandler("report", report_handler))
    app.add_handler(MessageHandler(filters.Regex("^📈 Отчёт$"), report_handler))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, freeform_handler))
    app.add_handler(CommandHandler("help", help_handler))

    app.run_polling()


if __name__ == "__main__":
    main()
