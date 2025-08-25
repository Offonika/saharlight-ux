# файл: services/api/alembic/env.py
import logging
from logging.config import fileConfig
import os
import sys
from urllib.parse import quote_plus

from alembic import context
from sqlalchemy import engine_from_config, pool


logger = logging.getLogger(__name__)

# === ЛОГИРОВАНИЕ ===
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# === PYTHONPATH: добавим корень репозитория, чтобы импортировать app.* ===
# .../services/api/alembic -> поднимаемся на два уровня к services/api, затем к корню
HERE = os.path.dirname(os.path.abspath(__file__))  # .../services/api/alembic
API_DIR = os.path.dirname(HERE)  # .../services/api
REPO_ROOT = os.path.dirname(API_DIR)  # .../saharlight-ux
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# === ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ ОКРУЖЕНИЯ ===
try:
    from dotenv import load_dotenv
except ImportError:
    # "python-dotenv" is optional; ignore if it's missing.
    pass
else:
    load_dotenv()

# === ИМПОРТ НАСТРОЕК И МОДЕЛЕЙ ===
# Ожидаем, что в app/diabetes/models.py определён Base
try:
    from services.api.app.config import settings  # FastAPI/Pydantic settings
except Exception:
    # альтернативный импорт, если пакетная структура другая
    from app.config import settings  # type: ignore

try:
    from services.api.app.diabetes.services.db import Base
except Exception:
    from app.diabetes.services.db import Base  # type: ignore

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

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
