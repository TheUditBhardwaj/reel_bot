"""
Configuration management using Pydantic Settings.

Loads environment variables from .env file and provides
type-safe access throughout the application.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Core ──────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_NAME: str = "ReelMind AI"
    LOG_LEVEL: str = "INFO"
    PORT: int = 8080

    # ── Telegram ──────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str
    WEBHOOK_URL: Optional[str] = None  # e.g. https://your-app.railway.app
    WEBHOOK_SECRET: Optional[str] = None  # Secret token for webhook verification

    # ── NVIDIA / Mistral AI ───────────────────────────────────────────
    NVIDIA_API_KEY: str
    NVIDIA_MODEL: str = "mistralai/mistral-large-3-675b-instruct-2512"

    # ── Whisper ───────────────────────────────────────────────────────
    WHISPER_MODEL: str = "base"  # tiny | base | small | medium | large

    # ── Database ──────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://localhost:5432/reelmind"

    # ── ChromaDB ──────────────────────────────────────────────────────
    CHROMA_PERSIST_DIR: str = "./chroma_data"

    # ── Notion (Optional) ────────────────────────────────────────────
    NOTION_API_KEY: Optional[str] = None
    NOTION_DATABASE_ID: Optional[str] = None

    # ── yt-dlp ────────────────────────────────────────────────────────
    COOKIE_FILE: Optional[str] = None  # Path to cookies.txt for Instagram auth
    DOWNLOAD_DIR: str = "/tmp/reelmind_downloads"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def notion_enabled(self) -> bool:
        return bool(self.NOTION_API_KEY and self.NOTION_DATABASE_ID)

    @property
    def webhook_enabled(self) -> bool:
        return bool(self.WEBHOOK_URL)


@lru_cache()
def get_settings() -> Settings:
    """Return cached singleton Settings instance."""
    return Settings()
