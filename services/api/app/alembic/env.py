# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import pool
from alembic import context

import os
import sys
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv(".env")
sys.path.append(os.getcwd())

# Импорт конфигурации проекта
from diabetes.services.db import Base
from backend.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

# Alembic Config
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from sqlalchemy import create_engine
    connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
