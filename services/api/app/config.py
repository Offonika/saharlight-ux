"""Application configuration loaded from environment variables."""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Always attempt to load variables from a local .env file.
load_dotenv()


def _read_log_level() -> int:
    """Return numeric log level from ``LOG_LEVEL``."""
    raw = os.getenv("LOG_LEVEL", "")
    if raw.lower() in {"1", "true", "debug"}:
        return logging.DEBUG
    return logging.INFO


# --- Logging -----------------------------------------------------------------
LOG_LEVEL: int = _read_log_level()
"""Logging verbosity level for the application."""


# --- Database -----------------------------------------------------------------
DB_HOST: str = os.getenv("DB_HOST", "localhost")
"""Hostname of the database server."""

_raw_db_port = os.getenv("DB_PORT", "5432")
try:
    DB_PORT: int = int(_raw_db_port)
except ValueError:  # pragma: no cover - logging only
    logger.error("Invalid DB_PORT %r; defaulting to 5432", _raw_db_port)
    DB_PORT = 5432
"""Port number of the database server."""

DB_NAME: str = os.getenv("DB_NAME", "diabetes_bot")
"""Name of the database to use."""

DB_USER: str = os.getenv("DB_USER", "diabetes_user")
"""Database username."""

DB_PASSWORD: str | None = os.getenv("DB_PASSWORD")
"""Password for the database user."""


# --- Runtime ------------------------------------------------------------------
_raw_uvicorn_workers = os.getenv("UVICORN_WORKERS", "1")
try:
    UVICORN_WORKERS: int = int(_raw_uvicorn_workers)
except ValueError:  # pragma: no cover - logging only
    logger.error(
        "Invalid UVICORN_WORKERS %r; defaulting to 1", _raw_uvicorn_workers
    )
    UVICORN_WORKERS = 1
"""Number of worker processes for Uvicorn."""

