# bot.py

from diabetes.handlers import register_handlers
from diabetes.db import init_db
from diabetes.config import TELEGRAM_TOKEN
from telegram.ext import ApplicationBuilder
import logging
import sys

logging.basicConfig(level=logging.INFO)
logging.info("=== Bot started ===")

def main():
    if not TELEGRAM_TOKEN:
        logging.error("TELEGRAM_TOKEN is not set. Please provide the environment variable.")
        sys.exit(1)

    init_db()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    register_handlers(app)
    app.run_polling()

if __name__ == "__main__":
    main()

