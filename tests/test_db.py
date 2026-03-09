import os
import subprocess
import sys
import time

import pytest
from sqlalchemy import text

from office_hero.db.engine import create_async_engine
from office_hero.db.session import get_session


@pytest.fixture(autouse=True, scope="session")
def ensure_database_available():
    """Make sure a PostgreSQL server is reachable for the integration tests.

    This fixture will attempt to start Rancher Desktop (Windows only) if the
    Docker CLI is not responsive, then launch a disposable Postgres container
    named **oh-test-db**.  It also sets ``DATABASE_URL`` if not already
    configured so the test itself can just read it.
    """
    # first, ensure Docker itself is running
    try:
        subprocess.run(
            ["docker", "info"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception:
        # try to bring up Rancher Desktop on Windows
        if sys.platform == "win32":
            rd_paths = [
                r"C:\Program Files\Rancher Desktop\rancher-desktop.exe",
                r"C:\Program Files\Rancher Desktop\Rancher.Desktop.exe",
            ]
            for rd in rd_paths:
                if os.path.exists(rd):
                    subprocess.Popen([rd])
                    # give Rancher Desktop a moment to initialise Docker
                    time.sleep(10)
                    break
        # recheck docker availability
        try:
            subprocess.run(
                ["docker", "info"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pytest.skip(
                "Docker daemon is not available; ensure Rancher Desktop or Docker is running"
            )

    # ensure the test database container is running
    try:
        ps = subprocess.run(
            ["docker", "ps", "-q", "-f", "name=oh-test-db"],
            check=True,
            capture_output=True,
            text=True,
        )
        if not ps.stdout.strip():
            subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--name",
                    "oh-test-db",
                    "-e",
                    "POSTGRES_PASSWORD=pass",
                    "-e",
                    "POSTGRES_DB=test",
                    "-p",
                    "5432:5432",
                    "-d",
                    "postgres:15-alpine",
                ],
                check=True,
            )
            # wait for the container's postgres to be accepting connections
            for _ in range(20):
                out = subprocess.run(
                    ["docker", "exec", "oh-test-db", "pg_isready", "-U", "postgres"],
                    capture_output=True,
                    text=True,
                )
                if "accepting connections" in out.stdout:
                    break
                time.sleep(1)
            # extra grace period after pg_isready — asyncpg can still fail
            # with "unexpected connection_lost()" if pg is not fully warmed up
            time.sleep(2)
    except Exception as exc:
        pytest.skip(f"Unable to ensure database container: {exc}")

    # finally, export the URL if not set
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:pass@localhost/test",
    )


def test_db_connection_and_rls():
    # integration test: requires a live database URL in DATABASE_URL env
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not configured")

    import asyncio

    async def run():
        engine = create_async_engine(url)
        async with get_session(engine, tenant_id="00000000-0000-0000-0000-000000000000") as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
            # tenant_id should have been set by the context manager above
            r = await session.execute(text("SELECT current_setting('app.tenant_id')"))
            assert r.scalar() == "00000000-0000-0000-0000-000000000000"
        await engine.dispose()

    try:
        asyncio.run(run())
    except (ConnectionError, OSError) as exc:
        pytest.skip(f"Database not reachable (infrastructure not ready): {exc}")
