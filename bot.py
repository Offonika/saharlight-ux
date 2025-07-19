# bot.py

from diabetes.handlers import register_handlers
from diabetes.db import init_db
from diabetes.config import TELEGRAM_TOKEN
from telegram.ext import ApplicationBuilder
import logging

logging.basicConfig(level=logging.INFO)
logging.info("=== Bot started ===")

def main():
    init_db()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    register_handlers(app)
    app.run_polling()

if __name__ == "__main__":
    main()

