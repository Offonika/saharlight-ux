from __future__ import annotations

import datetime
import logging
import os
import re

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ExtBot,
    JobQueue,
    MessageHandler,
    filters,
)
from sqlalchemy.exc import SQLAlchemyError
from typing import TYPE_CHECKING, TypeAlias


from .common_handlers import help_command, smart_input_help
from .router import callback_router
from . import learning_handlers
from services.api.app.diabetes import learning_handlers as dynamic_learning_handlers
from ..utils.ui import (
    PROFILE_BUTTON_TEXT,
    REMINDERS_BUTTON_TEXT,
    REPORT_BUTTON_TEXT,
    HISTORY_BUTTON_TEXT,
    PHOTO_BUTTON_PATTERN,
    QUICK_INPUT_BUTTON_TEXT,
    HELP_BUTTON_TEXT,
    SOS_BUTTON_TEXT,
    SUBSCRIPTION_BUTTON_TEXT,
)
from services.api.app.ui.keyboard import LEARN_BUTTON_TEXT

OLD_LEARN_BUTTON_TEXT = "🎓 Обучение"
LEARN_BUTTON_ALIASES: tuple[str, ...] = (
    LEARN_BUTTON_TEXT,
    OLD_LEARN_BUTTON_TEXT,
)
LEARN_BUTTON_PATTERN: re.Pattern[str] = re.compile(
    r"^(?:" + "|".join(re.escape(text) for text in LEARN_BUTTON_ALIASES) + r")$"
)

logger = logging.getLogger(__name__)

GPT_MODE_KEY = "gpt_mode"
GPT_TIMEOUT = datetime.timedelta(minutes=5)


async def _gpt_timeout(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear GPT dialog flag on timeout."""
    job = context.job
    user_id = job.data if job is not None else None
    if not isinstance(user_id, int):
        return
    user_data = context.application.user_data.get(user_id)
    if isinstance(user_data, dict):
        user_data.pop(GPT_MODE_KEY, None)


async def start_gpt_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Activate GPT dialog mode and schedule its timeout."""
    message = update.message
    if message is None:
        return
    if context.user_data is None:
        context.user_data = {}
    context.user_data[GPT_MODE_KEY] = True
    jq = context.job_queue
    user = update.effective_user
    if jq and user is not None:
        job_name = f"gpt_timeout_{user.id}"
        for job in jq.get_jobs_by_name(job_name):
            job.schedule_removal()
        jq.run_once(
            _gpt_timeout,
            when=GPT_TIMEOUT,
            name=job_name,
            data=user.id,
        )
    await message.reply_text(
        "💬 GPT режим активирован. Напишите сообщение или /cancel для выхода."
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancel current operation and clear GPT dialog flag."""
    if context.user_data is not None:
        context.user_data.pop(GPT_MODE_KEY, None)
    jq = context.job_queue
    user = update.effective_user
    if jq and user is not None:
        job_name = f"gpt_timeout_{user.id}"
        for job in jq.get_jobs_by_name(job_name):
            job.schedule_removal()
    from . import dose_calc

    await dose_calc.dose_cancel(update, context)


if TYPE_CHECKING:
    CommandHandlerT: TypeAlias = CommandHandler[ContextTypes.DEFAULT_TYPE, object]
    MessageHandlerT: TypeAlias = MessageHandler[ContextTypes.DEFAULT_TYPE, object]
    CallbackQueryHandlerT: TypeAlias = CallbackQueryHandler[
        ContextTypes.DEFAULT_TYPE, object
    ]
else:
    CommandHandlerT = CommandHandler
    MessageHandlerT = MessageHandler
    CallbackQueryHandlerT = CallbackQueryHandler


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
    except (RuntimeError, ImportError) as exc:
        handler_name = "register_debug_reminder_handlers"
        logger.error("Failed to load %s: %s", handler_name, exc)
        raise RuntimeError(f"{handler_name} failed") from exc

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
    from services.api.app.diabetes import commands as bot_commands
    from services.api.app.config import reload_settings, settings
    from services.api.app.assistant.repositories.logs import cleanup_old_logs
    from services.api.app.assistant.services.memory_service import cleanup_old_memory

    reload_settings()
    learning_env = os.getenv("LEARNING_MODE_ENABLED")
    if learning_env is not None:
        learning_enabled = learning_env.lower() not in {"0", "false"}
    else:
        learning_enabled = settings.learning_mode_enabled

    app.add_handler(CommandHandlerT("menu", learning_handlers.cmd_menu))
    app.add_handler(
        MessageHandlerT(
            filters.TEXT & filters.Regex(LEARN_BUTTON_PATTERN),
            dynamic_learning_handlers.learn_command,
        )
    )
    app.add_handler(CommandHandlerT("report", reporting_handlers.report_request))
    app.add_handler(CommandHandlerT("history", reporting_handlers.history_view))
    app.add_handler(dose_calc.dose_conv)
    # Register profile conversation before sugar conversation so that numeric
    # inputs for profile aren't captured by sugar logging
    register_profile_handlers(app)
    app.add_handler(sugar_handlers.sugar_conv)
    app.add_handler(sos_handlers.sos_contact_conv)
    app.add_handler(CommandHandlerT("cancel", cancel))
    app.add_handler(CommandHandlerT("help", help_command))
    app.add_handler(CommandHandlerT("reset_onboarding", bot_commands.reset_onboarding))
    if learning_enabled:
        learning_handlers.register_handlers(app)
    app.add_handler(CommandHandlerT("gpt", start_gpt_dialog))
    app.add_handler(CommandHandlerT("reset", bot_commands.reset_command))
    app.add_handler(CommandHandlerT("trial", billing_handlers.trial_command))
    app.add_handler(CommandHandlerT("upgrade", billing_handlers.upgrade_command))
    app.add_handler(
        CallbackQueryHandlerT(billing_handlers.trial_command, pattern="^trial$")
    )
    register_reminder_handlers(app)
    app.add_handler(CommandHandlerT("alertstats", alert_handlers.alert_stats))
    app.add_handler(CommandHandlerT("hypoalert", security_handlers.hypo_alert_faq))
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
            filters.Regex(PHOTO_BUTTON_PATTERN), photo_handlers.photo_prompt
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
            filters.Regex(re.escape(SUBSCRIPTION_BUTTON_TEXT)),
            billing_handlers.subscription_button,
        )
    )
    app.add_handler(
        MessageHandlerT(
            filters.Regex(re.escape(SOS_BUTTON_TEXT)),
            sos_handlers.sos_contact_start,
        )
    )
    app.add_handler(
        MessageHandlerT(
            filters.TEXT & ~filters.COMMAND,
            dynamic_learning_handlers.on_any_text,
            block=False,
        ),
        group=0,
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

        async def _cleanup(_context: ContextTypes.DEFAULT_TYPE) -> None:
            await cleanup_old_logs()
            await cleanup_old_memory()

        jq.run_repeating(
            _cleanup,
            interval=datetime.timedelta(days=1),
            first=datetime.timedelta(hours=1),
            name="cleanup_old_records",
        )
