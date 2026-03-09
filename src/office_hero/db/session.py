from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from office_hero.db.engine import create_engine


@asynccontextmanager
async def get_session(engine=None) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session, setting the RLS tenant_id variable automatically."""
    if engine is None:
        engine = create_engine()
    async with AsyncSession(engine) as session:  # type: ignore[misc]
        # set the tenant id session variable to whatever has been stashed
        # on the FastAPI app object; callers may set app.tenant_id in middleware
        from sqlalchemy import text

        # we can't import Request directly here because this module also
        # is used in background jobs where no request object exists. instead
        # we read from a global thread-local if available.
        try:
            from starlette_context import context

            tenant = context.get("tenant_id")
        except ImportError:
            tenant = None

        if tenant:
            await session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant})
        yield session
        await session.commit()
