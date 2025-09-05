from __future__ import annotations

import logging
import os

from telegram.ext import Application

from .diabetes.bot_start_handlers import build_start_handler

logger = logging.getLogger(__name__)


def main() -> None:
    """Run the telegram bot with the /start WebApp links."""

    token = os.environ["TELEGRAM_TOKEN"]
    ui_base_url = os.environ.get("UI_BASE_URL", "/ui")
    application = Application.builder().token(token).build()
    application.add_handler(build_start_handler(ui_base_url))
    application.run_polling()


if __name__ == "__main__":
    main()
