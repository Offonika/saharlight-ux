from __future__ import annotations

import logging
import os
from pathlib import Path

from telegram.ext import Application, PicklePersistence

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

    state_dir = os.environ.get("STATE_DIRECTORY", "/var/lib/diabetes-bot")
    default_path = os.path.join(state_dir, "bot_persistence.pkl")
    persistence_file = Path(os.environ.get("BOT_PERSISTENCE_PATH", default_path))
    persistence_file.parent.mkdir(parents=True, exist_ok=True)
    persistence = PicklePersistence(str(persistence_file), single_file=True)

    application = Application.builder().token(token).persistence(persistence).build()
    application.add_handler(build_start_handler(ui_base_url))
    application.add_handler(build_status_handler(ui_base_url, api_base_url))
    application.run_polling()


if __name__ == "__main__":
    main()
