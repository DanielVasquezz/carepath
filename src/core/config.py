"""
CarePath — Application Configuration
=====================================
Central settings management usando Pydantic Settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List


class Settings(BaseSettings):
    # ── App ─────────────────────────────
    APP_NAME: str = "CarePath"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = "CarePath API"
    DEBUG: bool = True

    # ── API ─────────────────────────────
    API_V1_PREFIX: str = "/api/v1"

    # ── CORS ────────────────────────────
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # ── Security ────────────────────────
    SECRET_KEY: str = "dev_secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ── DB ──────────────────────────────
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_NAME: str = "carepath_db"
    CLOUD_SQL_INSTANCE: Optional[str] = None

    # ── AI / LLM (OpenAI) ───────────────
    OPENAI_API_KEY: str = "tu_key_aqui"
    LLM_MODEL: str = "gpt-4o-mini"

    @property
    def DATABASE_URL(self) -> str:
        """
        Genera dinámicamente la URL de conexión para SQLAlchemy.
        """
        return (
            f"postgresql+asyncpg://"
            f"{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/"
            f"{self.DB_NAME}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()