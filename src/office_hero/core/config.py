"""Application configuration via environment variables using pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    database_url: str
    jwt_private_key: str
    jwt_public_key: str
    jwt_algorithm: str = "RS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_settings() -> Settings:
    """Lazily load settings once."""
    return Settings()
