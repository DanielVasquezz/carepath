"""
CarePath — Application Configuration
=====================================
Central settings management using Pydantic Settings.

Why centralize settings here?
Because configuration scattered across files is the #1 cause
of "works on my machine" bugs. One file. One source of truth.

Environment variables override defaults automatically.
In production (AWS), these come from environment variables.
In development, they come from the .env file.
The code never changes — only the environment does.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Pydantic validates every setting on startup.
    If DATABASE_URL is missing in production, the app
    refuses to start with a clear error — not a cryptic
    runtime failure 10 minutes later.
    """
    
    # ── Application ──────────────────────────────────────
    APP_NAME: str = "CarePath"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = (
        "Intelligent medical triage and follow-up system powered by AI"
    )
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"  
    
    # ── Database ──────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/carepath"
    )
    
    # ── Security ──────────────────────────────────────────
    SECRET_KEY: str = "change-this-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # ── AI / LLM ──────────────────────────────────────────
    OPENAI_API_KEY: str = "sk-placeholder"
    LLM_MODEL: str = "gpt-4o-mini"
    LL_MAX_TOKENS: int = 1000
    
    # ── CORS ──────────────────────────────────────────────
    # Which frontend domains can call our API
    
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",    # React dev server
        "http://localhost:8080",    # Vue dev server
        "https://carepath.app",     # production frontend
    ]  
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

# Singleton — one instance shared across the entire app
# Import this wherever you need settings:
# from src.core.config import settings
settings = Settings()