import os

import pytest
from office_hero.db.engine import create_async_engine
from office_hero.db.session import get_session


def test_db_connection_and_rls():
    # integration test: requires a live database URL in DATABASE_URL env
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not configured")

    import asyncio

    async def run():
        engine = create_async_engine(url)
        async with get_session(engine) as session:
            result = await session.execute("SELECT 1")
            assert result.scalar() == 1
            await session.execute(
                "SET LOCAL app.tenant_id = '00000000-0000-0000-0000-000000000000'"
            )
            r = await session.execute("SELECT current_setting('app.tenant_id')")
            assert r.scalar() == "00000000-0000-0000-0000-000000000000"
        await engine.dispose()

    asyncio.run(run())
