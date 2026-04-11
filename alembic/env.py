import sys
from os import path
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from alembic import context

# ─── CONFIGURACIÓN DE RUTAS ───────────────────────────────────────
# Esto permite que Alembic encuentre el módulo 'src' en la raíz
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from src.core.config import settings
from src.core.database import Base
from src.models.db.patient_db import PatientDB      # noqa: F401
from src.models.db.triage_db import SymptomDB, TriageCaseDB  # noqa: F401
# ──────────────────────────────────────────────────────────────────

# Objeto de configuración de Alembic
config = context.config

# Interpretar el archivo de log
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata de los modelos
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    # Usamos la property y reemplazamos el driver
    url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")

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
    # Reemplazamos +asyncpg por +psycopg2 para que Alembic pueda conectar
    sync_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")

    # Creamos el engine síncrono
    connectable = create_engine(
        sync_url,
        poolclass=pool.NullPool,
    )

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