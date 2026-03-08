from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


@asynccontextmanager
async def get_session(
    engine: AsyncEngine, *, tenant_id: str | None = None
) -> AsyncGenerator[AsyncSession, None]:
    """Provide an async SQLAlchemy session.

    The returned object is an :class:`~sqlalchemy.ext.asyncio.AsyncSession`
    suitable for use with ``async with``.

    If ``tenant_id`` is supplied the session will immediately execute a
    ``SET LOCAL app.tenant_id = '<tenant_id>'`` statement on the connection.  This
    is the mechanism by which the service layer configures PostgreSQL row-level
    security (RLS) for the current tenant.  Application middleware will pass the
    actual UUID extracted from the authenticated JWT.

    ``tenant_id`` defaults to ``None``; callers that wish to manage the session
    variable themselves may omit it.

    Usage::

        async with get_session(engine, tenant_id=some_uuid) as session:
            await session.execute(...)
    """

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:  # type: AsyncSession
        if tenant_id is not None:
            # ``SET LOCAL`` only affects the current transaction/connection.
            await session.execute(text(f"SET LOCAL app.tenant_id = '{tenant_id}'"))
        yield session
