from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker as _sa_async_sessionmaker

from office_hero.db.engine import create_engine

# Expose as a module-level name so tests can monkeypatch it without replacing
# the SQLAlchemy import.  ``get_session`` looks this up in the module namespace
# at call time, so ``monkeypatch.setattr(session_mod, "async_sessionmaker", …)``
# takes effect immediately.
async_sessionmaker = _sa_async_sessionmaker


@asynccontextmanager
async def get_session(
    engine: Any = None, *, tenant_id: str | None = None
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session, optionally setting the RLS tenant_id variable.

    Args:
        engine: An ``AsyncEngine`` instance.  Defaults to the engine built from
            ``DATABASE_URL``.
        tenant_id: When provided, executes ``SET LOCAL app.tenant_id`` before
            yielding the session so that RLS policies are applied for this
            request.  Falls back to the starlette-context value when omitted.
    """
    if engine is None:
        engine = create_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        _tenant = tenant_id
        if _tenant is None:
            # fall back to starlette-context when running inside a web request
            try:
                from starlette_context import context

                _tenant = context.get("tenant_id")
            except ImportError:
                pass
        if _tenant:
            # Use string interpolation rather than bind params: asyncpg does not
            # support parameter placeholders ($1, $2 …) in SET LOCAL statements.
            await session.execute(text(f"SET LOCAL app.tenant_id = '{_tenant}'"))
        yield session
