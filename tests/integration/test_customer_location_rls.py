"""Integration tests for Customer/Location tenant isolation via PostgreSQL RLS.

These tests require a real PostgreSQL instance (Neon branch in CI) with the
slice-9 migration applied. They are skipped automatically when ``DATABASE_URL``
is not set so that the standard unit/API test run remains DB-free.

Each test sets ``app.tenant_id`` via ``SET LOCAL`` (ADR 053) and asserts that
RLS silently hides cross-tenant rows — the row appears not to exist rather
than yielding a 403.
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

pytestmark = pytest.mark.integration


_DATABASE_URL = os.environ.get("DATABASE_URL")


@pytest.fixture()
def database_url() -> str:
    """Return DATABASE_URL or skip the test."""
    if not _DATABASE_URL:
        pytest.skip("DATABASE_URL not set — RLS integration tests skipped")
    return _DATABASE_URL


@pytest.fixture()
async def engine(database_url):
    """Async SQLAlchemy engine pointing at the test database."""
    eng = create_async_engine(database_url, future=True)
    yield eng
    await eng.dispose()


async def _set_tenant(session, tenant_id) -> None:
    await session.execute(text(f"SET LOCAL app.tenant_id = '{tenant_id}'"))


@pytest.mark.asyncio
async def test_tenant_a_cannot_select_tenant_b_customer_via_rls(engine):
    """Tenant A's session must not see Tenant B's customer rows.

    Insert a customer as tenant B, then in a tenant-A session attempt to
    SELECT that customer's id. Expect 0 rows (RLS silently hides the row).
    """
    tenant_a = uuid4()
    tenant_b = uuid4()

    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    # Insert a tenant_b customer using a session scoped to tenant_b.
    async with sessionmaker() as session:
        await _set_tenant(session, tenant_b)
        result = await session.execute(
            text("""
                INSERT INTO customers (id, tenant_id, name, archived)
                VALUES (gen_random_uuid(), :tenant_id, :name, false)
                RETURNING id
                """),
            {"tenant_id": str(tenant_b), "name": "Tenant B Customer"},
        )
        tenant_b_customer_id = result.scalar_one()
        await session.commit()

    # Read in a tenant_a session — RLS should hide the row.
    async with sessionmaker() as session:
        await _set_tenant(session, tenant_a)
        result = await session.execute(
            text("SELECT id FROM customers WHERE id = :cid"),
            {"cid": str(tenant_b_customer_id)},
        )
        rows = result.all()
        assert rows == [], "RLS leak: tenant A can see tenant B's customer"


@pytest.mark.asyncio
async def test_cascade_delete_locations_when_customer_hard_deleted(engine):
    """Hard-deleting a customer cascades to its locations (FK ON DELETE CASCADE)."""
    tenant_id = uuid4()
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async with sessionmaker() as session:
        await _set_tenant(session, tenant_id)
        cust = (
            await session.execute(
                text("""
                    INSERT INTO customers (id, tenant_id, name, archived)
                    VALUES (gen_random_uuid(), :tenant_id, :name, false)
                    RETURNING id
                    """),
                {"tenant_id": str(tenant_id), "name": "DeleteMe"},
            )
        ).scalar_one()
        await session.execute(
            text("""
                INSERT INTO locations (
                    id, tenant_id, customer_id,
                    street, city, state, postal_code, country,
                    geocode_status, archived
                ) VALUES (
                    gen_random_uuid(), :tenant_id, :customer_id,
                    '123 Main', 'Philadelphia', 'PA', '19103', 'US',
                    'pending', false
                )
                """),
            {"tenant_id": str(tenant_id), "customer_id": str(cust)},
        )
        await session.commit()

        await session.execute(text("DELETE FROM customers WHERE id = :cid"), {"cid": str(cust)})
        await session.commit()

        remaining = (
            await session.execute(
                text("SELECT count(*) FROM locations WHERE customer_id = :cid"),
                {"cid": str(cust)},
            )
        ).scalar_one()
        assert remaining == 0
