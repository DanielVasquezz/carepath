# src/core/database.py
"""
CarePath — Database Connection Layer
======================================
Manages the PostgreSQL connection pool and session lifecycle.

Key concepts:
  Engine      → the connection to the database
  Session     → a unit of work with the database
  Session Factory → creates sessions on demand

Why async?
Because database queries block while waiting for the disk/network.
Async lets the server handle other requests during that wait.
With 100 simultaneous patients, this is the difference between
a responsive system and a frozen one.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.core.config import settings


# ── Engine ────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    # echo=True prints every SQL query to console in development
    # Invaluable for debugging, but too noisy for production
    pool_size=10,
    # How many database connections to keep open and ready
    # Each connection can serve one query at a time
    # 10 connections = 10 simultaneous DB operations
    max_overflow=20,
    # Extra connections allowed beyond pool_size when under load
    # Total maximum: pool_size + max_overflow = 30 connections
    pool_pre_ping=True,
    # Before using a connection from the pool, test if it's alive
    # Prevents errors after the DB restarts or times out idle connections
)

# ── Session Factory ───────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    # expire_on_commit=False means objects don't become invalid
    # after a commit. Without this, accessing patient.id after
    # db.commit() would trigger another database query.
    # In async code, unexpected queries cause hard-to-debug errors.
)

# ── Base Model ────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy database models.

    Every database table in CarePath inherits from this.
    It provides:
      - Metadata registry (table names, columns, relationships)
      - Common behavior across all models
      - The foundation for Alembic migrations

    Naming convention: SQL models live in src/models/db/
    Pydantic models live in src/models/
    They are separate on purpose — different responsibilities.
    """
    pass


# ── Dependency ────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.

    Usage in any endpoint:
        async def my_endpoint(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Patient))

    Lifecycle per request:
        1. Request arrives
        2. get_db() opens a new session
        3. Session is injected into the endpoint function
        4. Endpoint runs its queries
        5. Session commits (if no errors) or rolls back (if error)
        6. Session closes — connection returns to pool

    The 'yield' makes this a context manager.
    Code before yield = setup.
    Code after yield = cleanup (always runs, even on error).
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()