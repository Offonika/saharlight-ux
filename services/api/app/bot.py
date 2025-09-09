from __future__ import annotations

import logging
import os

from telegram.ext import Application

from .diabetes.bot_start_handlers import build_start_handler
from .diabetes.bot_status_handlers import build_status_handler

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the telegram bot with the /start WebApp links and status command."""

    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN is not set")
        raise RuntimeError("TELEGRAM_TOKEN is not configured")
    ui_base_url = os.environ.get("UI_BASE_URL", "/ui")
    api_base_url = os.environ.get("API_BASE_URL", "/api")
    application = Application.builder().token(token).build()
    application.add_handler(build_start_handler(ui_base_url))
    application.add_handler(build_status_handler(ui_base_url, api_base_url))
    application.run_polling()


if __name__ == "__main__":
    main()
