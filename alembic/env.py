# alembic/env.py
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# ─── AGREGA ESTAS 4 LÍNEAS AQUÍ ───────────────────────────────────
from src.core.config import settings
from src.core.database import Base
from src.models.db.patient_db import PatientDB      # noqa: F401
from src.models.db.triage_db import SymptomDB, TriageCaseDB  # noqa: F401
# ──────────────────────────────────────────────────────────────────

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ─── CAMBIA ESTA LÍNEA ────────────────────────────────────────────
# ANTES: target_metadata = None
# DESPUÉS:
target_metadata = Base.metadata
# ──────────────────────────────────────────────────────────────────


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""

    # ─── CAMBIA ESTA LÍNEA DENTRO DE run_migrations_offline ───────
    # ANTES: url = config.get_main_option("sqlalchemy.url")
    # DESPUÉS:
    url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")
    # ──────────────────────────────────────────────────────────────

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    # ─── REEMPLAZA TODA ESTA SECCIÓN ──────────────────────────────
    # ANTES era: connectable = engine_from_config(...)
    # DESPUÉS:
    from sqlalchemy import create_engine

    connectable = create_engine(
        settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")
    )
    # ──────────────────────────────────────────────────────────────

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()