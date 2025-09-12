from __future__ import annotations

import logging
import os

from telegram.ext import Application

from services.bot.main import build_persistence

from .diabetes.bot_start_handlers import build_start_handler
from .diabetes.bot_status_handlers import build_status_handler

logger = logging.getLogger(__name__)


def get_api_base_url() -> str:
    """Return API base URL from environment.

    Prefers ``API_URL`` but falls back to the deprecated ``API_BASE_URL``.
    Defaults to ``/api`` when neither variable is set.
    """

    api_url = os.environ.get("API_URL")
    if api_url:
        return api_url
    api_base_url = os.environ.get("API_BASE_URL")
    if api_base_url:
        return api_base_url
    return "/api"


def main() -> None:
    """Run the telegram bot with the /start WebApp links and status command."""

    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN is not set")
        raise RuntimeError("TELEGRAM_TOKEN is not configured")
    ui_base_url = os.environ.get("UI_BASE_URL", "/ui")
    api_base_url = get_api_base_url()

    persistence = build_persistence()

    application = Application.builder().token(token).persistence(persistence).build()
    application.add_handler(build_start_handler(ui_base_url))
    application.add_handler(build_status_handler(ui_base_url, api_base_url))
    application.run_polling()


if __name__ == "__main__":
    main()
