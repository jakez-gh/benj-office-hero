from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import create_async_engine as sa_create_async_engine
from sqlalchemy.pool import NullPool


def create_async_engine(url: str | None = None) -> AsyncEngine:
    """Create an AsyncEngine configured from `DATABASE_URL` env or explicit URL.

    Uses NullPool by default to avoid connection sharing issues in serverless
    environments; you can override via environment variables if needed.
    """
    database_url = url or os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL must be provided as argument or set in environment")
    # URL should be of form postgresql+asyncpg://...
    return sa_create_async_engine(
        database_url,
        echo=False,
        poolclass=NullPool,
        future=True,
    )


# alias for backwards compatibility
create_engine = create_async_engine
# internal reference exposed so tests can monkeypatch the underlying factory
_create_async_engine = sa_create_async_engine
