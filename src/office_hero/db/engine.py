from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool


def create_async_engine_from_url(url: str | None = None) -> AsyncEngine:
    """Create an AsyncEngine configured from `DATABASE_URL`.

    Uses NullPool by default to avoid connection sharing issues in serverless
    environments; you can override via environment variables if needed.
    """
    from pydantic import BaseSettings

    class Settings(BaseSettings):
        database_url: str

        class Config:
            env_prefix = ""

    settings = Settings()
    database_url = url or settings.database_url
    # URL should be of form postgresql+asyncpg://...
    return create_async_engine(
        database_url,
        echo=False,
        poolclass=NullPool,
        future=True,
    )


# alias for easier import
create_engine = create_async_engine_from_url
