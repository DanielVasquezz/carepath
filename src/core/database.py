from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from src.core.config import settings


# ─────────────────────────────
# BASE
# ─────────────────────────────
class Base(DeclarativeBase):
    pass


# ─────────────────────────────
# ENGINE CONFIG (CLOUD + LOCAL)
# ─────────────────────────────
def build_database_url() -> str:
    """
    Construye URL segura para Cloud SQL o local.
    """

    if settings.CLOUD_SQL_INSTANCE and settings.DB_USER:
        # CLOUD SQL vía proxy o connector (RECOMENDADO proxy)
        return (
            f"postgresql+asyncpg://"
            f"{settings.DB_USER}:{settings.DB_PASSWORD}"
            f"@/{settings.DB_NAME}"
        )

    # LOCAL
    return settings.DATABASE_URL


engine = create_async_engine(
    build_database_url(),
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)


# ─────────────────────────────
# SESSION FACTORY
# ─────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ─────────────────────────────
# DEPENDENCY FASTAPI
# ─────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()

        except Exception:
            await session.rollback()
            raise