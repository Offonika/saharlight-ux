# file: services/api/alembic/env.py
from __future__ import annotations

import os
from logging.config import fileConfig
from urllib.parse import quote_plus
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool  # используем create_engine — без set_main_option

# Загружаем .env: сначала корень, затем сервисный (сервисный перекрывает)
try:
    from dotenv import load_dotenv

    _HERE = Path(__file__).resolve()
    root_env = _HERE.parents[3] / ".env"  # <repo_root>/.env
    service_env = _HERE.parents[1] / ".env"  # services/api/.env
    load_dotenv(root_env)
    load_dotenv(service_env, override=True)
except Exception:
    pass

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = None  # миграции ручные, metadata не требуется


def build_db_url() -> str:
    # 1) DATABASE_URL, если задан
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    # 2) Собираем из DB_* (экранируем пароль)
    user = os.getenv("DB_USER", "")
    pwd = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "")
    pwd_enc = quote_plus(pwd) if pwd else ""
    return f"postgresql+psycopg2://{user}:{pwd_enc}@{host}:{port}/{name}"


def run_migrations_offline() -> None:
    url = build_db_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = build_db_url()
    # создаём движок напрямую — никаких проблем с '%' и configparser
    engine = create_engine(url, poolclass=pool.NullPool, future=True)
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                compare_server_default=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
