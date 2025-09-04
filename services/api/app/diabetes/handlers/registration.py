from __future__ import annotations

import datetime
import logging
import re

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
from typing import TYPE_CHECKING, TypeAlias

from .onboarding_handlers import onboarding_conv, onboarding_poll_answer
from .common_handlers import menu_command, help_command, smart_input_help
from .router import callback_router
from ..utils.ui import (
    PROFILE_BUTTON_TEXT,
    REMINDERS_BUTTON_TEXT,
    REPORT_BUTTON_TEXT,
    HISTORY_BUTTON_TEXT,
    PHOTO_BUTTON_TEXT,
    QUICK_INPUT_BUTTON_TEXT,
    HELP_BUTTON_TEXT,
    SOS_BUTTON_TEXT,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    CommandHandlerT: TypeAlias = CommandHandler[ContextTypes.DEFAULT_TYPE, object]
    MessageHandlerT: TypeAlias = MessageHandler[ContextTypes.DEFAULT_TYPE, object]
    CallbackQueryHandlerT: TypeAlias = CallbackQueryHandler[
        ContextTypes.DEFAULT_TYPE, object
    ]
    PollAnswerHandlerT: TypeAlias = PollAnswerHandler[ContextTypes.DEFAULT_TYPE, object]
else:
    CommandHandlerT = CommandHandler
    MessageHandlerT = MessageHandler
    CallbackQueryHandlerT = CallbackQueryHandler
    PollAnswerHandlerT = PollAnswerHandler


def register_profile_handlers(
    app: Application[
        ExtBot[None],
        ContextTypes.DEFAULT_TYPE,
        dict[str, object],
        dict[str, object],
        dict[str, object],
        JobQueue[ContextTypes.DEFAULT_TYPE],
    ],
) -> None:
    """Register profile-related handlers."""

    from . import profile

    app.add_handler(profile.profile_conv)
    app.add_handler(profile.profile_webapp_handler)
    app.add_handler(
        MessageHandlerT(
            filters.Regex(re.escape(PROFILE_BUTTON_TEXT)), profile.profile_view
        )
    )
    app.add_handler(
        CallbackQueryHandlerT(profile.profile_security, pattern="^profile_security")
    )
    app.add_handler(
        CallbackQueryHandlerT(profile.profile_back, pattern="^profile_back$")
    )


def register_reminder_handlers(
    app: Application[
        ExtBot[None],
        ContextTypes.DEFAULT_TYPE,
        dict[str, object],
        dict[str, object],
        dict[str, object],
        JobQueue[ContextTypes.DEFAULT_TYPE],
    ],
) -> None:
    """Register reminder-related handlers and schedule reminders."""

    from . import reminder_handlers

    app.add_handler(CommandHandlerT("reminders", reminder_handlers.reminders_list))
    app.add_handler(CommandHandlerT("addreminder", reminder_handlers.add_reminder))
    app.add_handler(reminder_handlers.reminder_action_handler)
    app.add_handler(reminder_handlers.reminder_webapp_handler)
    app.add_handler(CommandHandlerT("delreminder", reminder_handlers.delete_reminder))
    app.add_handler(
        MessageHandlerT(
            filters.Regex(re.escape(REMINDERS_BUTTON_TEXT)),
            reminder_handlers.reminders_list,
        )
    )
    app.add_handler(
        CallbackQueryHandlerT(reminder_handlers.reminder_callback, pattern="^remind_")
    )

    # --- DEBUG HANDLERS ---
    try:
        from services.api.app.diabetes.handlers.reminder_debug import (
            register_debug_reminder_handlers,
        )

        register_debug_reminder_handlers(app)
    except ImportError as e:
        logger.warning("⚠️ Could not load debug reminder handlers: %s", e)
    except Exception:
        logger.exception("Failed to load debug reminder handlers")
        raise

    # --- Schedule reminders ---
    job_queue = app.job_queue
    if job_queue:
        try:
            reminder_handlers.schedule_all(job_queue)
        except SQLAlchemyError:
            logger.exception("Failed to schedule reminders")


def register_handlers(
    app: Application[
        ExtBot[None],
        ContextTypes.DEFAULT_TYPE,
        dict[str, object],
        dict[str, object],
        dict[str, object],
        JobQueue[ContextTypes.DEFAULT_TYPE],
    ],
) -> None:
    """Register bot handlers on the provided ``Application`` instance."""

    # Import inside the function to avoid heavy imports at module import time
    # (for example OpenAI client initialization).
    from . import (
        dose_calc,
        reporting_handlers,
        alert_handlers,
        sos_handlers,
        security_handlers,
        photo_handlers,
        sugar_handlers,
        gpt_handlers,
        billing_handlers,
    )
    from . import learning_handlers

    app.add_handler(onboarding_conv)
    app.add_handler(CommandHandlerT("menu", menu_command))
    app.add_handler(CommandHandlerT("report", reporting_handlers.report_request))
    app.add_handler(CommandHandlerT("history", reporting_handlers.history_view))
    app.add_handler(dose_calc.dose_conv)
    # Register profile conversation before sugar conversation so that numeric
    # inputs for profile aren't captured by sugar logging
    register_profile_handlers(app)
    app.add_handler(sugar_handlers.sugar_conv)
    app.add_handler(sos_handlers.sos_contact_conv)
    app.add_handler(CommandHandlerT("cancel", dose_calc.dose_cancel))
    app.add_handler(CommandHandlerT("help", help_command))
    app.add_handler(CommandHandlerT("learn", learning_handlers.learn_command))
    app.add_handler(CommandHandlerT("lesson", learning_handlers.lesson_command))
    app.add_handler(CommandHandlerT("quiz", learning_handlers.quiz_command))
    app.add_handler(CommandHandlerT("progress", learning_handlers.progress_command))
    app.add_handler(CommandHandlerT("exit", learning_handlers.exit_command))
    app.add_handler(CommandHandlerT("gpt", gpt_handlers.chat_with_gpt))
    app.add_handler(CommandHandlerT("trial", billing_handlers.trial_command))
    app.add_handler(CommandHandlerT("upgrade", billing_handlers.upgrade_command))
    register_reminder_handlers(app)
    app.add_handler(CommandHandlerT("alertstats", alert_handlers.alert_stats))
    app.add_handler(CommandHandlerT("hypoalert", security_handlers.hypo_alert_faq))
    app.add_handler(PollAnswerHandlerT(onboarding_poll_answer))
    app.add_handler(
        MessageHandlerT(
            filters.Regex(re.escape(REPORT_BUTTON_TEXT)),
            reporting_handlers.report_request,
        )
    )
    app.add_handler(
        MessageHandlerT(
            filters.Regex(re.escape(HISTORY_BUTTON_TEXT)),
            reporting_handlers.history_view,
        )
    )
    app.add_handler(
        MessageHandlerT(
            filters.Regex(re.escape(PHOTO_BUTTON_TEXT)), photo_handlers.photo_prompt
        )
    )
    app.add_handler(
        MessageHandlerT(
            filters.Regex(re.escape(QUICK_INPUT_BUTTON_TEXT)), smart_input_help
        )
    )
    app.add_handler(
        MessageHandlerT(filters.Regex(re.escape(HELP_BUTTON_TEXT)), help_command)
    )
    app.add_handler(
        MessageHandlerT(
            filters.Regex(re.escape(SOS_BUTTON_TEXT)),
            sos_handlers.sos_contact_start,
        )
    )
    app.add_handler(
        MessageHandlerT(filters.TEXT & ~filters.COMMAND, gpt_handlers.freeform_handler)
    )
    app.add_handler(MessageHandlerT(filters.PHOTO, photo_handlers.photo_handler))
    app.add_handler(MessageHandlerT(filters.Document.IMAGE, photo_handlers.doc_handler))
    app.add_handler(
        CallbackQueryHandlerT(
            reporting_handlers.report_period_callback, pattern="^report_back$"
        )
    )
    app.add_handler(
        CallbackQueryHandlerT(
            reporting_handlers.report_period_callback, pattern="^report_period:"
        )
    )
    app.add_handler(CallbackQueryHandlerT(callback_router))

    async def _clear_waiting_flags(context: ContextTypes.DEFAULT_TYPE) -> None:
        for data in context.application.user_data.values():
            data.pop(photo_handlers.WAITING_GPT_FLAG, None)
            data.pop(photo_handlers.WAITING_GPT_TIMESTAMP, None)

    jq = app.job_queue
    if jq:
        jq.run_once(
            _clear_waiting_flags,
            when=datetime.timedelta(seconds=0),
            name="clear_waiting_gpt_flags_once",
        )
        jq.run_repeating(
            _clear_waiting_flags,
            interval=datetime.timedelta(hours=1),
            name="clear_waiting_gpt_flags",
        )
