"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: Literal["development", "production", "test"] = "development"

    # Database
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/splitwise"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_refresh_secret: str = "change-me-refresh-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # CORS
    frontend_url: str = "http://localhost:5173"

    # Rate limiting
    rate_limit_enabled: bool = True

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_test(self) -> bool:
        return self.environment == "test"

    @property
    def cors_origins(self) -> list[str]:
        # Allow comma-separated list in addition to the single frontend URL.
        origins = [o.strip() for o in self.frontend_url.split(",") if o.strip()]
        if not self.is_production:
            origins.append("http://localhost:5173")
        return list(set(origins))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
