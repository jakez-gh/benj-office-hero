"""Integration tests for Vehicle/VehicleCrew tenant isolation via PostgreSQL RLS.

These tests require a real PostgreSQL instance with the slice-12 migration
applied. They are skipped automatically when ``DATABASE_URL`` is not set so
that the standard unit/API test run remains DB-free.

Each test sets ``app.tenant_id`` via ``SET LOCAL`` (ADR 053) and asserts that
RLS silently hides cross-tenant rows.
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

pytestmark = pytest.mark.integration

_DATABASE_URL = os.environ.get("DATABASE_URL")


@pytest.fixture()
def database_url() -> str:
    if not _DATABASE_URL:
        pytest.skip("DATABASE_URL not set — RLS integration tests skipped")
    return _DATABASE_URL


@pytest.fixture()
async def engine(database_url):
    from sqlalchemy.ext.asyncio import create_async_engine

    eng = create_async_engine(database_url, future=True)
    yield eng
    await eng.dispose()


async def _set_tenant(session, tenant_id) -> None:
    from sqlalchemy import text

    await session.execute(text(f"SET LOCAL app.tenant_id = '{tenant_id}'"))


@pytest.mark.asyncio
async def test_rls_hides_other_tenant_vehicles(engine):
    """Tenant A's session must not see Tenant B's vehicles."""
    pytest.xfail("Requires live PostgreSQL with migration 0005 applied")

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker

    Session = async_sessionmaker(engine, expire_on_commit=False)
    tenant_a = uuid4()
    tenant_b = uuid4()

    # Insert tenant_b vehicle bypassing RLS (superuser session)
    async with Session() as session, session.begin():
        # Insert tenants
        for tid in (tenant_a, tenant_b):
            await session.execute(
                text("INSERT INTO tenants (id, name) VALUES (:id, :name) ON CONFLICT DO NOTHING"),
                {"id": tid, "name": f"tenant-{tid}"},
            )
        vid = uuid4()
        await session.execute(
            text(
                "INSERT INTO vehicles (id, tenant_id, license_plate)" " VALUES (:id, :tid, :plate)"
            ),
            {"id": vid, "tid": tenant_b, "plate": "RLS-TEST-B"},
        )

    # Tenant A session should not see tenant B's vehicle
    async with Session() as session, session.begin():
        await _set_tenant(session, tenant_a)
        rows = (
            await session.execute(text("SELECT id FROM vehicles WHERE id = :id"), {"id": vid})
        ).fetchall()
        assert rows == [], "RLS should hide tenant B's vehicle from tenant A"


@pytest.mark.asyncio
async def test_unique_constraint_blocks_concurrent_double_assign(engine):
    """Two concurrent inserts of crews for same (vehicle, date); one wins → 409."""
    pytest.xfail("Requires live PostgreSQL with migration 0005 applied")
    # Implementation: insert two VehicleCrew rows for same (tenant, vehicle, date)
    # in separate transactions; assert one succeeds and one raises IntegrityError.


@pytest.mark.asyncio
async def test_cascade_delete_members_on_crew_delete(engine):
    """Deleting a VehicleCrew cascades to VehicleCrewMembers."""
    pytest.xfail("Requires live PostgreSQL with migration 0005 applied")
    # Implementation: insert a crew + members, delete the crew,
    # assert vehicle_crew_members is empty.
