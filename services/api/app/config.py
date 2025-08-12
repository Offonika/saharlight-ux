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
_raw_maintainer_chat_id = os.getenv("MAINTAINER_CHAT_ID")
MAINTAINER_CHAT_ID = None
if _raw_maintainer_chat_id:
    try:
        MAINTAINER_CHAT_ID = int(_raw_maintainer_chat_id)
    except ValueError:
        logger.warning("Invalid MAINTAINER_CHAT_ID %r", _raw_maintainer_chat_id)
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

# Base URL of the API service
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Number of worker processes for uvicorn when running the API server
_raw_uvicorn_workers = os.getenv("UVICORN_WORKERS", "1")
try:
    UVICORN_WORKERS = int(_raw_uvicorn_workers)
except ValueError:
    logger.error(
        "Invalid UVICORN_WORKERS %r; defaulting to 1", _raw_uvicorn_workers
    )
    UVICORN_WORKERS = 1
