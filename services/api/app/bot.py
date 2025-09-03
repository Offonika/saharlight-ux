from __future__ import annotations

import logging
import os

from telegram.ext import Application

from .diabetes.handlers.onboarding_handlers import onboarding_conv

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the telegram bot with onboarding handler."""

    token = os.environ["TELEGRAM_TOKEN"]
    application = Application.builder().token(token).build()
    application.add_handler(onboarding_conv)
    application.run_polling()


if __name__ == "__main__":
    main()
