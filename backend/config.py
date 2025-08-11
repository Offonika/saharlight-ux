import logging
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

if not os.getenv("SKIP_DOTENV"):
    load_dotenv()  # Загрузка переменных из .env файла


def _read_log_level() -> int:
    """Return log level based on environment variables."""
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
_raw_db_port = os.getenv("DB_PORT", "5432")
try:
    DB_PORT = int(_raw_db_port)
except ValueError:
    logger.error("Invalid DB_PORT %r; defaulting to 5432", _raw_db_port)
    DB_PORT = 5432
DB_NAME = os.getenv("DB_NAME", "diabetes_bot")
DB_USER = os.getenv("DB_USER", "diabetes_user")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Optional directory containing custom fonts for PDF reports
FONT_DIR = os.getenv("FONT_DIR")

# Validate and normalize web app URL
_raw_webapp_url = os.getenv("WEBAPP_URL")
WEBAPP_URL = None
if not _raw_webapp_url:
    logger.warning("WEBAPP_URL is not set; web app integration disabled")
elif not _raw_webapp_url.startswith("https://"):
    logger.warning(
        "Ignoring WEBAPP_URL %r because it is not HTTPS; web app integration disabled",
        _raw_webapp_url,
    )
else:
    WEBAPP_URL = _raw_webapp_url
