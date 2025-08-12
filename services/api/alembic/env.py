# alembic/env.py
from logging.config import fileConfig
from sqlalchemy import pool
from alembic import context

import os
from pathlib import Path
from urllib.parse import quote_plus

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover
    def load_dotenv(*_args, **_kwargs):  # type: ignore
        return None
else:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def build_db_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    user = os.getenv("DB_USER", "")
    password = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "")
    port = os.getenv("DB_PORT", "")
    name = os.getenv("DB_NAME", "")

    if not password:
        raise RuntimeError("DB_PASSWORD is missing; ensure .env is loaded")

    return f"postgresql+psycopg2://{user}:{quote_plus(password)}@{host}:{port}/{name}"


def run_migrations_offline() -> None:
    url = build_db_url()
    if not url or url.startswith("driver://"):
        raise RuntimeError("Invalid database URL")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from sqlalchemy import create_engine

    url = build_db_url()
    if not url or url.startswith("driver://"):
        raise RuntimeError("Invalid database URL")

    config.set_main_option("sqlalchemy.url", url)
    connectable = create_engine(url, poolclass=pool.NullPool)

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
