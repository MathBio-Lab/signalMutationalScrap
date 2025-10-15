from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlmodel import SQLModel
from app.config.environment import settings
from app.database.models import *
from alembic import context
from sqlalchemy import create_engine, pool
import sqlmodel

config = context.config
target_metadata = SQLModel.metadata


if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def get_url():
    user = settings.DATABASE_USER
    password = settings.DATABASE_PASSWORD
    host = settings.DATABASE_HOST
    port = settings.DATABASE_PORT
    db = settings.DATABASE_NAME
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
