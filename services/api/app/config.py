"""Application configuration via Pydantic settings."""

from __future__ import annotations

import logging
import os
import threading
from typing import Literal, Optional

from pydantic import AliasChoices, Field, field_validator

try:  # pragma: no cover - import guard
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ModuleNotFoundError as exc:  # pragma: no cover - executed at import time
    raise ImportError("`pydantic-settings` is required. Install it with `pip install pydantic-settings`.") from exc


logger = logging.getLogger(__name__)

_settings_lock: threading.Lock = threading.Lock()

TOPICS_RU: dict[str, str] = {
    "xe_basics": "Хлебные единицы",
    "healthy-eating": "Здоровое питание",
    "basics-of-diabetes": "Основы диабета",
    "insulin-usage": "Инсулин",
}


class Settings(BaseSettings):
    """Runtime application configuration.

    Environment variables are loaded from ``.env`` located in the project root.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    # General application settings
    app_name: str = "diabetes-bot"
    debug: bool = False

    photos_dir: str = Field(default="/var/lib/diabetes-bot/photos", alias="PHOTOS_DIR")

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
    db_read_role: Optional[str] = Field(default=None, alias="DB_READ_ROLE")
    db_write_role: Optional[str] = Field(default=None, alias="DB_WRITE_ROLE")

    # Logging and runtime
    log_level: int = Field(default=logging.INFO, alias="LOG_LEVEL")
    uvicorn_workers: int = Field(default=1, alias="UVICORN_WORKERS")

    # Optional service URLs and API keys
    public_origin: str = Field(default="", alias="PUBLIC_ORIGIN")
    ui_base_url: str = Field(default="/ui", alias="UI_BASE_URL")
    api_url: Optional[str] = Field(default=None, alias="API_URL")
    subscription_url: Optional[str] = Field(default=None, alias="SUBSCRIPTION_URL")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_assistant_id: Optional[str] = Field(default=None, alias="OPENAI_ASSISTANT_ID")
    openai_command_model: str = Field(default="gpt-4o-mini", alias="OPENAI_COMMAND_MODEL")
    api_key_min_length: int = Field(default=32, alias="API_KEY_MIN_LENGTH")
    assistant_mode_enabled: bool = Field(
        default=True,
        alias="ASSISTANT_MODE_ENABLED",
        description="Enable assistant mode",
    )
    learning_mode_enabled: bool = Field(
        default=True,
        alias="LEARNING_MODE_ENABLED",
        validation_alias=AliasChoices("LEARNING_MODE_ENABLED", "LEARNING_ENABLED"),
    )
    assistant_max_turns: int = Field(
        default=16,
        alias="ASSISTANT_MAX_TURNS",
        description="Max turns kept in memory",
    )
    assistant_summary_trigger: int = Field(
        default=12,
        alias="ASSISTANT_SUMMARY_TRIGGER",
        description="Turns before conversation is summarized",
    )
    learning_model_default: str = Field(default="gpt-4o-mini", alias="LEARNING_MODEL_DEFAULT")
    learning_prompt_cache: bool = Field(default=True, alias="LEARNING_PROMPT_CACHE")
    learning_prompt_cache_size: int = Field(default=128, alias="LEARNING_PROMPT_CACHE_SIZE")
    learning_prompt_cache_ttl_sec: int = Field(
        default=28800,
        alias="LEARNING_PROMPT_CACHE_TTL_SEC",
        description="TTL of prompt cache in seconds",
    )
    learning_content_mode: Literal["dynamic", "static"] = Field(default="dynamic", alias="LEARNING_CONTENT_MODE")
    learning_ui_show_topics: bool = Field(default=False, alias="LEARNING_UI_SHOW_TOPICS")
    learning_logging_required: bool = Field(default=False, alias="LEARNING_LOGGING_REQUIRED")
    learning_reply_mode: Literal["two_messages", "one_message"] = Field(
        default="two_messages", alias="LEARNING_REPLY_MODE"
    )
    pending_log_limit: int = Field(
        default=100,
        alias="PENDING_LOG_LIMIT",
        description="Max pending lesson logs kept in memory",
    )
    lesson_logs_ttl_days: int = Field(default=14, alias="LESSON_LOGS_TTL_DAYS")
    assistant_memory_ttl_days: int = Field(default=60, alias="ASSISTANT_MEMORY_TTL_DAYS")
    openai_proxy: Optional[str] = Field(default=None, alias="OPENAI_PROXY")
    learning_assistant_id: Optional[str] = Field(default=None, alias="LEARNING_ASSISTANT_ID")
    learning_command_model: str = Field(default="gpt-4o-mini", alias="LEARNING_COMMAND_MODEL")
    learning_planner_model: str = Field(
        default="gpt-4o-mini",
        alias="LEARNING_PLANNER_MODEL",
        description="Model used for lesson planning",
    )
    font_dir: Optional[str] = Field(default=None, alias="FONT_DIR")
    onboarding_video_url: Optional[str] = Field(default=None, alias="ONBOARDING_VIDEO_URL")
    telegram_token: Optional[str] = Field(default=None, alias="TELEGRAM_TOKEN")
    telegram_payments_provider_token: Optional[str] = Field(default=None, alias="TELEGRAM_PAYMENTS_PROVIDER_TOKEN")
    internal_api_key: Optional[str] = Field(default=None, alias="INTERNAL_API_KEY")
    admin_id: Optional[int] = Field(default=None, alias="ADMIN_ID")

    @field_validator("log_level", mode="before")
    @classmethod
    def parse_log_level(cls, v: int | str | None) -> int:  # pragma: no cover - simple parsing
        if isinstance(v, str):
            v_lower = v.lower()
            level_map: dict[str, int] = {
                "critical": logging.CRITICAL,
                "error": logging.ERROR,
                "warning": logging.WARNING,
                "info": logging.INFO,
                "debug": logging.DEBUG,
                "notset": logging.NOTSET,
            }
            if v_lower in level_map:
                return level_map[v_lower]
            if v_lower in {"1", "true"}:
                return logging.DEBUG
            try:
                return int(v)
            except ValueError:
                return logging.INFO
        if isinstance(v, int):
            return v
        return logging.INFO

    @property
    def learning_enabled(self) -> bool:
        """Backward compatibility alias for ``learning_mode_enabled``."""

        return self.learning_mode_enabled


# Instantiate settings for external use
settings = Settings()


def get_settings() -> Settings:
    """Return the current application settings."""

    return settings


def reload_settings() -> Settings:
    """Reload settings from the environment and return them.

    Thread-safe: a module-level lock guards reinitialization of ``settings``.
    """

    global settings
    with _settings_lock:
        settings = Settings()
        return settings


def get_db_password() -> Optional[str]:
    """Return the database password from the environment.

    ``Settings`` loads variables from a ``.env`` file which can cache values
    across imports. Tests dynamically mutate ``DB_PASSWORD`` and expect those
    changes to be reflected immediately. Querying ``os.environ`` directly
    ensures we always get the current value and avoids any cached defaults.
    """

    return os.environ.get("DB_PASSWORD")


def get_db_read_password() -> Optional[str]:
    """Return the read-only database role password from the environment."""

    return os.environ.get("DB_READ_PASSWORD")


def get_db_write_password() -> Optional[str]:
    """Return the write database role password from the environment."""

    return os.environ.get("DB_WRITE_PASSWORD")


def build_ui_url(path: str) -> str:
    """Return an absolute UI URL for ``path``.

    Slashes are normalized and ``settings.public_origin`` must be configured.
    ``settings.ui_base_url`` is stripped of leading and trailing slashes.
    """

    if not settings.public_origin:
        raise RuntimeError("PUBLIC_ORIGIN not configured")
    origin = settings.public_origin.rstrip("/")
    base = settings.ui_base_url.strip("/")
    rel = path.lstrip("/")
    if base:
        return f"{origin}/{base}/{rel}"
    return f"{origin}/{rel}"


__all__ = [
    "TOPICS_RU",
    "Settings",
    "settings",
    "get_settings",
    "reload_settings",
    "get_db_password",
    "get_db_read_password",
    "get_db_write_password",
    "build_ui_url",
]
