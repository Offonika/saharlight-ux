from __future__ import annotations

import logging
import os

from telegram.ext import Application, CommandHandler

from .diabetes.handlers.learning_handlers import lesson_command, quiz_command
from .diabetes.handlers.onboarding_handlers import onboarding_conv

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the telegram bot with onboarding handler."""

    token = os.environ["TELEGRAM_TOKEN"]
    application = Application.builder().token(token).build()
    application.add_handler(onboarding_conv)
    application.add_handler(CommandHandler("lesson", lesson_command))
    application.add_handler(CommandHandler("quiz", quiz_command))
    application.run_polling()


if __name__ == "__main__":
    main()
