# файл: services/api/alembic/env.py
import logging
import os
import sys
from logging.config import fileConfig
from pathlib import Path
from urllib.parse import quote_plus

from alembic import context
from sqlalchemy import engine_from_config, pool


logger = logging.getLogger(__name__)

# === ЛОГИРОВАНИЕ ===
config = context.config
if hasattr(config, "set_main_option"):
    config.set_main_option("script_location", str(Path(__file__).resolve().parent))
    config.set_main_option(
        "version_locations", str(Path(__file__).resolve().parent / "versions")
    )
if getattr(config, "config_file_name", None) is not None:
    fileConfig(config.config_file_name)

# === PYTHONPATH: добавим корень репозитория, чтобы импортировать app.* ===
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# === ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ ОКРУЖЕНИЯ ===
try:
    from dotenv import load_dotenv
except ImportError:
    # "python-dotenv" is optional; ignore if it's missing.
    logger.debug("python-dotenv is not installed; skipping .env loading")
else:
    load_dotenv()

# === ИМПОРТ НАСТРОЕК И МОДЕЛЕЙ ===
# Ожидаем, что в app/diabetes/models.py определён Base
try:
    from services.api.app.config import settings  # FastAPI/Pydantic settings
except ImportError:
    logger.info("services.api.app.config not found; falling back to app.config")
    # альтернативный импорт, если пакетная структура другая
    from app.config import settings  # type: ignore

try:
    from services.api.app.diabetes.services.db import Base
except ImportError:
    logger.info(
        "services.api.app.diabetes.services.db not found; falling back to app.diabetes.services.db"
    )
    from app.diabetes.services.db import Base  # type: ignore

# Ensure models are imported so Alembic's autogenerate can discover them
try:
    import services.api.app.diabetes.models  # noqa: F401
except ImportError:
    logger.info(
        "services.api.app.diabetes.models not found; falling back to app.diabetes.models"
    )
    import app.diabetes.models  # type: ignore  # noqa: F401

target_metadata = Base.metadata


def _compose_url_from_env() -> str | None:
    """
    Пытаемся собрать URL БД из переменных окружения, если DATABASE_URL не задан.
    Поддерживаем стандартные имена: DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME.
    """
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME")

    if user and password and name:
        return (
            f"postgresql+psycopg2://{user}:{quote_plus(password)}@{host}:{port}/{name}"
        )
    return None


def _get_database_url() -> str:
    # 1) Прямо из переменной окружения
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    # 2) Попытка собрать из отдельных переменных
    composed = _compose_url_from_env()
    if composed:
        return composed

    # 3) Из настроек приложения (Pydantic settings)
    # частые варианты имён поля:
    for attr in (
        "database_url",
        "DATABASE_URL",
        "sqlalchemy_database_url",
        "SQLALCHEMY_DATABASE_URL",
    ):
        if hasattr(settings, attr):
            val = getattr(settings, attr)
            if val:
                return str(val)

    raise RuntimeError(
        "Не найден URL базы данных. Задай переменную окружения DATABASE_URL "
        "или проверь settings.* (database_url / SQLALCHEMY_DATABASE_URL)."
    )


def run_migrations_offline() -> None:
    """Offline-режим: без подключения к БД."""
    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Online-режим: с подключением к БД."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _get_database_url()

    connectable = config.attributes.get("connection")
    if connectable is None:
        connectable = engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )
        connection = connectable.connect()
    else:
        connection = connectable

    with connection:
        is_sqlite = connection.dialect.name == "sqlite"
        # SQLite lacks many ALTER TABLE features; Alembic's "batch mode" rewrites
        # migrations by creating a new table and copying data so that schema
        # changes (like renaming or dropping columns) succeed.
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=is_sqlite,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
