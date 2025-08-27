from __future__ import annotations

import logging
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    PollAnswerHandler,
    filters,
)
from sqlalchemy.exc import SQLAlchemyError

from .onboarding_handlers import onboarding_conv, onboarding_poll_answer
from .common_handlers import menu_command, help_command, smart_input_help
from .router import callback_router

logger = logging.getLogger(__name__)


def register_handlers(app: Application) -> None:
    """Register bot handlers on the provided ``Application`` instance."""

    # Import inside the function to avoid heavy imports at module import time
    # (for example OpenAI client initialization).
    from .dose_handlers import (
        dose_conv,
        sugar_conv,
        dose_cancel,
        chat_with_gpt,
        freeform_handler,
        photo_handler,
        doc_handler,
        photo_prompt,
    )
    from .profile import (
        profile_conv,
        profile_webapp_handler,
        profile_view,
        profile_security,
        profile_back,
    )
    from .reporting_handlers import (
        report_request,
        history_view,
        report_period_callback,
    )
    from .reminder_handlers import (
        reminders_list,
        add_reminder,
        reminder_action_handler,
        reminder_webapp_handler,
        delete_reminder,
        reminder_callback,
        schedule_all,
    )
    from .alert_handlers import alert_stats
    from .sos_handlers import sos_contact_conv, sos_contact_start
    from .security_handlers import hypo_alert_faq

    app.add_handler(onboarding_conv)
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("report", report_request))
    app.add_handler(dose_conv)
    # Register profile conversation before sugar conversation so that numeric
    # inputs for profile aren't captured by sugar logging
    app.add_handler(profile_conv)
    app.add_handler(profile_webapp_handler)
    app.add_handler(sugar_conv)
    app.add_handler(sos_contact_conv)
    app.add_handler(CommandHandler("cancel", dose_cancel))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("gpt", chat_with_gpt))
    app.add_handler(CommandHandler("reminders", reminders_list))
    app.add_handler(CommandHandler("addreminder", add_reminder))
    app.add_handler(reminder_action_handler)
    app.add_handler(reminder_webapp_handler)
    app.add_handler(CommandHandler("delreminder", delete_reminder))
    app.add_handler(CommandHandler("alertstats", alert_stats))
    app.add_handler(CommandHandler("hypoalert", hypo_alert_faq))
    app.add_handler(PollAnswerHandler(onboarding_poll_answer))
    app.add_handler(MessageHandler(filters.Regex("^📄 Мой профиль$"), profile_view))
    app.add_handler(MessageHandler(filters.Regex("^📈 Отчёт$"), report_request))
    app.add_handler(MessageHandler(filters.Regex("^📊 История$"), history_view))
    app.add_handler(MessageHandler(filters.Regex("^📷 Фото еды$"), photo_prompt))
    app.add_handler(MessageHandler(filters.Regex("^🕹 Быстрый ввод$"), smart_input_help))
    app.add_handler(MessageHandler(filters.Regex("^⏰ Напоминания$"), reminders_list))
    app.add_handler(MessageHandler(filters.Regex("^ℹ️ Помощь$"), help_command))
    app.add_handler(MessageHandler(filters.Regex("^🆘 SOS контакт$"), sos_contact_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, freeform_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.Document.IMAGE, doc_handler))
    app.add_handler(CallbackQueryHandler(report_period_callback, pattern="^report_back$"))
    app.add_handler(
        CallbackQueryHandler(report_period_callback, pattern="^report_period:")
    )
    app.add_handler(CallbackQueryHandler(profile_security, pattern="^profile_security"))
    app.add_handler(CallbackQueryHandler(profile_back, pattern="^profile_back$"))
    app.add_handler(CallbackQueryHandler(reminder_callback, pattern="^remind_"))
    app.add_handler(CallbackQueryHandler(callback_router))

    job_queue = app.job_queue
    if job_queue:
        try:
            schedule_all(job_queue)
        except SQLAlchemyError:
            logger.exception("Failed to schedule reminders")


__all__ = ["register_handlers"]
