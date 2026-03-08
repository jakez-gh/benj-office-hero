from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


@asynccontextmanager
async def get_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Provide an async SQLAlchemy session.

    Usage::

        async with get_session(engine) as session:
            await session.execute(...)

    Currently this helper does not automatically set any session-local
    variables.  The calling code (e.g. integration tests or application
    middleware) is responsible for ``SET LOCAL app.tenant_id = ...`` when
    RLS is in use.
    """

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:  # type: AsyncSession
        yield session
