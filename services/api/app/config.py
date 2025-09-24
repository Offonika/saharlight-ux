"""Application configuration via Pydantic settings."""

from __future__ import annotations

import logging
import os
import posixpath
import threading
from typing import Literal, Optional, cast
from urllib.parse import urlsplit

from pydantic import AliasChoices, Field, field_validator

try:  # pragma: no cover - import guard
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ModuleNotFoundError as exc:  # pragma: no cover - executed at import time
    raise ImportError(
        "`pydantic-settings` is required. Install it with `pip install pydantic-settings`."
    ) from exc


logger = logging.getLogger(__name__)

_settings_lock: threading.Lock = threading.Lock()

_env_file_raw = os.environ.get("SAHARLIGHT_ENV_FILE", ".env")
_ENV_FILE: str | None = _env_file_raw.strip() or None

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
        env_file=_ENV_FILE,
        extra="ignore",
    )

    # General application settings
    app_name: str = "diabetes-bot"
    debug: bool = False

    allow_sync_db_fallback: bool = Field(
        default=True,
        alias="ALLOW_SYNC_DB_FALLBACK",
        description="Allow synchronous DB operations when async runner is missing",
    )

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

    # Redis configuration
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # Logging and runtime
    log_level: int = Field(default=logging.INFO, alias="LOG_LEVEL")
    uvicorn_workers: int = Field(default=1, alias="UVICORN_WORKERS")

    # Optional service URLs and API keys
    public_origin: str = Field(default="", alias="PUBLIC_ORIGIN")
    ui_base_url: str = Field(default="/ui", alias="UI_BASE_URL")
    webapp_url: Optional[str] = Field(default=None, alias="WEBAPP_URL")
    api_url: Optional[str] = Field(default=None, alias="API_URL")
    subscription_url: Optional[str] = Field(default=None, alias="SUBSCRIPTION_URL")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_assistant_id: Optional[str] = Field(
        default=None, alias="OPENAI_ASSISTANT_ID"
    )
    openai_command_model: str = Field(
        default="gpt-4o-mini", alias="OPENAI_COMMAND_MODEL"
    )
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
    assistant_default_mode: Literal["menu", "chat", "learn", "labs", "visit"] = Field(
        default="menu",
        alias="ASSISTANT_DEFAULT_MODE",
        description="Initial assistant mode",
    )
    assistant_menu_emoji: bool = Field(
        default=True,
        alias="ASSISTANT_MENU_EMOJI",
        description="Show emoji in assistant menu button",
    )
    learning_model_default: str = Field(
        default="gpt-4o-mini", alias="LEARNING_MODEL_DEFAULT"
    )
    learning_prompt_cache: bool = Field(default=True, alias="LEARNING_PROMPT_CACHE")
    learning_prompt_cache_size: int = Field(
        default=128, alias="LEARNING_PROMPT_CACHE_SIZE"
    )
    learning_prompt_cache_ttl_sec: int = Field(
        default=28800,
        alias="LEARNING_PROMPT_CACHE_TTL_SEC",
        description="TTL of prompt cache in seconds",
    )
    learning_content_mode: Literal["dynamic", "static"] = Field(
        default="dynamic", alias="LEARNING_CONTENT_MODE"
    )
    learning_ui_show_topics: bool = Field(
        default=False, alias="LEARNING_UI_SHOW_TOPICS"
    )
    learning_logging_required: bool = Field(
        default=False, alias="LEARNING_LOGGING_REQUIRED"
    )
    learning_reply_mode: Literal["two_messages", "one_message"] = Field(
        default="two_messages", alias="LEARNING_REPLY_MODE"
    )
    pending_log_limit: int = Field(
        default=100,
        alias="PENDING_LOG_LIMIT",
        description="Max pending lesson logs kept in memory",
    )
    lesson_logs_ttl_days: int = Field(default=14, alias="LESSON_LOGS_TTL_DAYS")
    assistant_memory_ttl_days: int = Field(
        default=60, alias="ASSISTANT_MEMORY_TTL_DAYS"
    )
    openai_proxy: Optional[str] = Field(default=None, alias="OPENAI_PROXY")
    learning_assistant_id: Optional[str] = Field(
        default=None, alias="LEARNING_ASSISTANT_ID"
    )
    learning_command_model: str = Field(
        default="gpt-4o-mini", alias="LEARNING_COMMAND_MODEL"
    )
    learning_planner_model: str = Field(
        default="gpt-4o-mini",
        alias="LEARNING_PLANNER_MODEL",
        description="Model used for lesson planning",
    )
    font_dir: Optional[str] = Field(default=None, alias="FONT_DIR")
    onboarding_video_url: Optional[str] = Field(
        default=None, alias="ONBOARDING_VIDEO_URL"
    )
    telegram_token: Optional[str] = Field(default=None, alias="TELEGRAM_TOKEN")
    telegram_payments_provider_token: Optional[str] = Field(
        default=None, alias="TELEGRAM_PAYMENTS_PROVIDER_TOKEN"
    )
    internal_api_key: Optional[str] = Field(default=None, alias="INTERNAL_API_KEY")
    admin_id: Optional[int] = Field(default=None, alias="ADMIN_ID")

    @field_validator("log_level", mode="before")
    @classmethod
    def parse_log_level(
        cls, v: int | str | None
    ) -> int:  # pragma: no cover - simple parsing
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


def _apply_settings(current: Settings, fresh: Settings) -> Settings:
    if type(current) is not type(fresh):
        try:
            current.__class__ = type(fresh)
        except TypeError:  # pragma: no cover - defensive guard
            logger.debug("Unable to update settings class", exc_info=True)

    current_fields = set(current.__dict__.keys())
    fresh_fields = set(type(fresh).model_fields.keys())

    for field in current_fields - fresh_fields:
        try:
            delattr(current, field)
        except AttributeError:
            current.__dict__.pop(field, None)

    for field in fresh_fields:
        setattr(current, field, getattr(fresh, field))

    object.__setattr__(
        current,
        "__pydantic_fields_set__",
        getattr(fresh, "__pydantic_fields_set__", set()).copy(),
    )

    return current



# Instantiate settings for external use.  When the module is reloaded via
# :func:`importlib.reload`, reuse the previously created instance so that other
# modules holding a reference to :data:`settings` continue to observe the
# refreshed values.
if "_settings_instance" in globals():
    _settings_instance = cast("Settings", globals()["_settings_instance"])
    _apply_settings(_settings_instance, Settings())
else:
    _settings_instance = Settings()

settings: Settings = _settings_instance


def get_settings() -> Settings:
    """Return the current application settings."""

    return _settings_instance


def reload_settings() -> Settings:
    """Reload settings from the environment while preserving identity.

    ``settings`` is mutated in place so that modules holding a direct
    reference to :data:`settings` continue to observe refreshed values after
    reloading. A module-level lock guards refreshes to keep the operation
    thread-safe.
    """

    with _settings_lock:
        fresh_settings = Settings()
        current = _apply_settings(_settings_instance, fresh_settings)
        return current



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
    """Return an absolute UI URL for ``path`` relative to ``public_origin``.

    ``path`` must be a relative URL segment. It is normalized so that duplicate
    slashes and ``.`` segments are collapsed, while ``..`` segments are
    rejected to prevent escaping from ``ui_base_url``. Query strings and
    fragments are preserved.
    """

    if not settings.public_origin:
        raise RuntimeError("PUBLIC_ORIGIN not configured")

    origin = settings.public_origin.rstrip("/")
    base = settings.ui_base_url.strip("/")

    parsed = urlsplit(path)
    if parsed.scheme or parsed.netloc:
        raise ValueError("UI path must be relative to PUBLIC_ORIGIN")

    relative_path = parsed.path.lstrip("/")
    if any(part == ".." for part in relative_path.split("/") if part):
        raise ValueError("UI path must not contain '..' segments")

    segments = [segment for segment in (base, relative_path) if segment]
    combined = "/".join(segments)
    normalized_path = posixpath.normpath(f"/{combined}" if combined else "/")
    if not normalized_path.startswith("/"):
        normalized_path = f"/{normalized_path}"

    should_have_trailing_slash = parsed.path.endswith("/") or (
        not parsed.path and bool(base)
    )
    if should_have_trailing_slash and normalized_path != "/":
        normalized_path = normalized_path.rstrip("/") + "/"

    base_prefix = base.strip("/")
    if base_prefix:
        expected_prefix = f"/{base_prefix}"
        if not (
            normalized_path == expected_prefix
            or normalized_path.startswith(f"{expected_prefix}/")
        ):
            raise ValueError("UI path escapes configured UI_BASE_URL")

    url = f"{origin}{normalized_path}"
    if parsed.query:
        url = f"{url}?{parsed.query}"
    if parsed.fragment:
        url = f"{url}#{parsed.fragment}"
    return url


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
