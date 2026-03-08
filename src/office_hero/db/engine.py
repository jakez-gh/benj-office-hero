import os
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import create_async_engine as _create_async_engine


def create_async_engine(url: str | None = None, **kwargs: Any) -> AsyncEngine:
    """Return a SQLAlchemy :class:`~sqlalchemy.ext.asyncio.AsyncEngine`.

    The ``DATABASE_URL`` environment variable is consulted if ``url`` is
    not provided.  A ``ValueError`` is raised when no URL can be found.

    Additional keyword arguments are passed through to
    ``sqlalchemy.ext.asyncio.create_async_engine``.
    """

    if url is None:
        url = os.environ.get("DATABASE_URL")
        if not url:
            raise ValueError("DATABASE_URL not configured")
    return _create_async_engine(url, **kwargs)
