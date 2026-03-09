from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import create_async_engine as _sa_create_async_engine
from sqlalchemy.pool import NullPool

# Expose as a module-level name so tests can monkeypatch it without touching
# SQLAlchemy internals.  create_async_engine() looks this up in the module
# namespace at call time, so monkeypatch.setattr(engine_mod, "_create_async_engine", …)
# takes effect immediately.
_create_async_engine = _sa_create_async_engine


def create_async_engine(url: str | None = None) -> AsyncEngine:
    """Create an AsyncEngine configured from `DATABASE_URL` env or explicit URL.

    Uses NullPool by default to avoid connection sharing issues in serverless
    environments; you can override via environment variables if needed.
    """
    database_url = url or os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL must be provided as argument or set in environment")
    # Call through the module-level alias so tests can monkeypatch _create_async_engine.
    return _create_async_engine(
        database_url,
        echo=False,
        poolclass=NullPool,
        future=True,
    )


# alias for backwards compatibility
create_engine = create_async_engine
