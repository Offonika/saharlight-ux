"""Application configuration loaded from environment variables."""

import logging
import os

from dotenv import load_dotenv


if not os.getenv("SKIP_DOTENV"):
    load_dotenv()  # Загрузка переменных из .env файла


def _read_log_level() -> int:
    """Return log level based on environment variables.

    The variable ``LOG_LEVEL`` takes precedence. If either ``LOG_LEVEL`` or
    ``DEBUG`` is set to one of ``{'1', 'true', 'debug'}`` (case-insensitive),
    ``logging.DEBUG`` is returned. Otherwise ``logging.INFO`` is used.
    """

    raw = os.getenv("LOG_LEVEL") or os.getenv("DEBUG") or ""
    if raw.lower() in {"1", "true", "debug"}:
        return logging.DEBUG
    return logging.INFO


LOG_LEVEL = _read_log_level()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")
OPENAI_PROXY = os.getenv("OPENAI_PROXY")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "diabetes_bot")
DB_USER = os.getenv("DB_USER", "diabetes_user")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Optional directory containing custom fonts for PDF reports
FONT_DIR = os.getenv("FONT_DIR")
WEBAPP_URL = os.getenv("WEBAPP_URL")
