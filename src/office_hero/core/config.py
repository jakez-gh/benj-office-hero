"""Application configuration via environment variables using pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # We deliberately avoid loading the .env file here because it
    # contains multiline RSA keys wrapped in triple-quotes.  The
    # bundled python-dotenv parser treats the inside of those strings as
    # separate variable assignments, which then show up as "extra"
    # inputs and cause pydantic validation to explode.  Configuration is
    # expected to come from the real environment in normal operation, so
    # tests that construct Settings() directly still work.
    model_config = SettingsConfigDict(
        env_file=None,
        case_sensitive=False,
        extra="ignore",  # ignore unrecognised vars
    )

    database_url: str
    jwt_private_key: str
    jwt_public_key: str
    jwt_algorithm: str = "RS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7


def get_settings() -> Settings:
    """Lazily load settings once."""
    return Settings()
