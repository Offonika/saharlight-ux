"""Application configuration via Pydantic settings."""

from __future__ import annotations

import logging
from typing import Optional

from pydantic import Field, field_validator

try:  # pragma: no cover - import guard
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ModuleNotFoundError as exc:  # pragma: no cover - executed at import time
    raise ImportError(
        "`pydantic-settings` is required. Install it with `pip install pydantic-settings`."
    ) from exc


class Settings(BaseSettings):
    """Runtime application configuration.

    Environment variables are loaded from ``infra/env/.env``.
    """

    model_config = SettingsConfigDict(
        env_file="infra/env/.env",
        extra="ignore",
    )

    # General application settings
    app_name: str = "diabetes-bot"
    debug: bool = False

    # Database configuration
    database_url: str = Field(
        default="postgresql://diabetes_user@localhost:5432/diabetes_bot",
        alias="DATABASE_URL",
    )
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="diabetes_bot", alias="DB_NAME")
    db_user: str = Field(default="diabetes_user", alias="DB_USER")
    db_password: Optional[str] = Field(default=None, alias="DB_PASSWORD")

    # Logging and runtime
    log_level: int = Field(default=logging.INFO, alias="LOG_LEVEL")
    uvicorn_workers: int = Field(default=1, alias="UVICORN_WORKERS")

    # Optional service URLs and API keys
    webapp_url: Optional[str] = Field(default=None, alias="WEBAPP_URL")
    api_url: Optional[str] = Field(default=None, alias="API_URL")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_assistant_id: Optional[str] = Field(default=None, alias="OPENAI_ASSISTANT_ID")
    openai_proxy: Optional[str] = Field(default=None, alias="OPENAI_PROXY")
    font_dir: Optional[str] = Field(default=None, alias="FONT_DIR")
    telegram_token: Optional[str] = Field(default=None, alias="TELEGRAM_TOKEN")

    @field_validator("log_level", mode="before")
    @classmethod
    def parse_log_level(cls, v: object) -> int:  # pragma: no cover - simple parsing
        if isinstance(v, str) and v.lower() in {"1", "true", "debug"}:
            return logging.DEBUG
        try:
            return int(v)  # type: ignore[return-value]
        except (TypeError, ValueError):
            return logging.INFO


# Instantiate settings for external use
settings = Settings()


# Legacy module-level variables for backward compatibility
LOG_LEVEL = settings.log_level
DB_HOST = settings.db_host
DB_PORT = settings.db_port
DB_NAME = settings.db_name
DB_USER = settings.db_user
DB_PASSWORD = settings.db_password
UVICORN_WORKERS = settings.uvicorn_workers
WEBAPP_URL = settings.webapp_url
API_URL = settings.api_url
OPENAI_API_KEY = settings.openai_api_key
OPENAI_ASSISTANT_ID = settings.openai_assistant_id
OPENAI_PROXY = settings.openai_proxy
FONT_DIR = settings.font_dir
TELEGRAM_TOKEN = settings.telegram_token

