# bot.py

from diabetes.handlers import register_handlers
from diabetes.db import init_db
from diabetes.config import TELEGRAM_TOKEN
from telegram.ext import ApplicationBuilder
import logging
import sys

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("=== Bot started ===")

    if not TELEGRAM_TOKEN:
        logger.error(
            "TELEGRAM_TOKEN is not set. Please provide the environment variable."
        )
        sys.exit(1)

    init_db()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    register_handlers(app)
    app.run_polling()

if __name__ == "__main__":
    main()

