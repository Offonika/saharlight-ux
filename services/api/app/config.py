"""Application configuration via Pydantic settings."""

from __future__ import annotations

import logging
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime application configuration.

    Environment variables are loaded from ``infra/env/.env``.
    """

    model_config = SettingsConfigDict(env_file="infra/env/.env")

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

