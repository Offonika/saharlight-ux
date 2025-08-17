from __future__ import annotations

import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ExtBot,
    JobQueue,
    MessageHandler,
    PollAnswerHandler,
    filters,
)
from sqlalchemy.exc import SQLAlchemyError

from .onboarding_handlers import onboarding_conv, onboarding_poll_answer
from .common_handlers import menu_command, help_command, smart_input_help
from .router import callback_router

logger = logging.getLogger(__name__)



def register_handlers(
    app: Application[
        ExtBot[None],
        ContextTypes.DEFAULT_TYPE,
        dict[str, object],
        dict[str, object],
        dict[str, object],
        JobQueue[ContextTypes.DEFAULT_TYPE],
    ]
) -> None:

    """Register bot handlers on the provided ``Application`` instance."""

    # Import inside the function to avoid heavy imports at module import time
    # (for example OpenAI client initialization).
    from . import (
        dose_handlers,
        profile,
        reporting_handlers,
        reminder_handlers,
        alert_handlers,
        sos_handlers,
        security_handlers,
    )

    app.add_handler(onboarding_conv)
    app.add_handler(CommandHandler[ContextTypes.DEFAULT_TYPE]("menu", menu_command))
    app.add_handler(CommandHandler[ContextTypes.DEFAULT_TYPE]("report", reporting_handlers.report_request))
    app.add_handler(dose_handlers.dose_conv)
    # Register profile conversation before sugar conversation so that numeric
    # inputs for profile aren't captured by sugar logging
    app.add_handler(profile.profile_conv)
    app.add_handler(profile.profile_webapp_handler)
    app.add_handler(dose_handlers.sugar_conv)
    app.add_handler(sos_handlers.sos_contact_conv)
    app.add_handler(CommandHandler[ContextTypes.DEFAULT_TYPE]("cancel", dose_handlers.dose_cancel))
    app.add_handler(CommandHandler[ContextTypes.DEFAULT_TYPE]("help", help_command))
    app.add_handler(CommandHandler[ContextTypes.DEFAULT_TYPE]("gpt", dose_handlers.chat_with_gpt))
    app.add_handler(CommandHandler[ContextTypes.DEFAULT_TYPE]("reminders", reminder_handlers.reminders_list))
    app.add_handler(CommandHandler[ContextTypes.DEFAULT_TYPE]("addreminder", reminder_handlers.add_reminder))
    app.add_handler(reminder_handlers.reminder_action_handler)
    app.add_handler(reminder_handlers.reminder_webapp_handler)
    app.add_handler(CommandHandler[ContextTypes.DEFAULT_TYPE]("delreminder", reminder_handlers.delete_reminder))
    app.add_handler(CommandHandler[ContextTypes.DEFAULT_TYPE]("alertstats", alert_handlers.alert_stats))
    app.add_handler(CommandHandler[ContextTypes.DEFAULT_TYPE]("hypoalert", security_handlers.hypo_alert_faq))
    app.add_handler(PollAnswerHandler[ContextTypes.DEFAULT_TYPE](onboarding_poll_answer))
    app.add_handler(
        MessageHandler[ContextTypes.DEFAULT_TYPE](filters.Regex("^📄 Мой профиль$"), profile.profile_view)
    )
    app.add_handler(
        MessageHandler[ContextTypes.DEFAULT_TYPE](filters.Regex("^📈 Отчёт$"), reporting_handlers.report_request)
    )
    app.add_handler(
        MessageHandler[ContextTypes.DEFAULT_TYPE](filters.Regex("^📊 История$"), reporting_handlers.history_view)
    )
    app.add_handler(
        MessageHandler[ContextTypes.DEFAULT_TYPE](filters.Regex("^📷 Фото еды$"), dose_handlers.photo_prompt)
    )
    app.add_handler(
        MessageHandler[ContextTypes.DEFAULT_TYPE](filters.Regex("^🕹 Быстрый ввод$"), smart_input_help)
    )
    app.add_handler(
        MessageHandler[ContextTypes.DEFAULT_TYPE](
            filters.Regex("^⏰ Напоминания$"), reminder_handlers.reminders_list
        )
    )
    app.add_handler(
        MessageHandler[ContextTypes.DEFAULT_TYPE](filters.Regex("^ℹ️ Помощь$"), help_command)
    )
    app.add_handler(
        MessageHandler[ContextTypes.DEFAULT_TYPE](
            filters.Regex("^🆘 SOS контакт$"), sos_handlers.sos_contact_start
        )
    )
    app.add_handler(
        MessageHandler[ContextTypes.DEFAULT_TYPE](
            filters.TEXT & ~filters.COMMAND, dose_handlers.freeform_handler
        )
    )
    app.add_handler(MessageHandler[ContextTypes.DEFAULT_TYPE](filters.PHOTO, dose_handlers.photo_handler))
    app.add_handler(
        MessageHandler[ContextTypes.DEFAULT_TYPE](filters.Document.IMAGE, dose_handlers.doc_handler)
    )
    app.add_handler(
        CallbackQueryHandler[ContextTypes.DEFAULT_TYPE](
            reporting_handlers.report_period_callback, pattern="^report_back$"
        )
    )
    app.add_handler(
        CallbackQueryHandler[ContextTypes.DEFAULT_TYPE](
            reporting_handlers.report_period_callback, pattern="^report_period:"
        )
    )
    app.add_handler(
        CallbackQueryHandler[ContextTypes.DEFAULT_TYPE](
            profile.profile_security, pattern="^profile_security"
        )
    )
    app.add_handler(
        CallbackQueryHandler[ContextTypes.DEFAULT_TYPE](profile.profile_back, pattern="^profile_back$")
    )
    app.add_handler(CallbackQueryHandler[ContextTypes.DEFAULT_TYPE](reminder_handlers.reminder_callback, pattern="^remind_"))
    app.add_handler(CallbackQueryHandler[ContextTypes.DEFAULT_TYPE](callback_router))

    job_queue = app.job_queue
    if job_queue:
        try:
            reminder_handlers.schedule_all(job_queue)
        except SQLAlchemyError:
            logger.exception("Failed to schedule reminders")
