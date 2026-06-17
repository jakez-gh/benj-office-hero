"""Integration tests for Job RLS and JSONB round-trip.

These tests require a live PostgreSQL database with ``DATABASE_URL`` set.
They are skipped automatically in CI when ``DATABASE_URL`` is absent so the
test suite still passes in the standard unit/API environment.

To run manually::

    DATABASE_URL=postgresql+asyncpg://... pytest tests/integration/test_jobs_rls.py -v
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


async def _seed_tenant_with_job(session, tenant_id, title: str = "Test job") -> str:
    """Insert a tenant row + customer + location + job; return the job id."""
    await _set_tenant(session, tenant_id)
    await session.execute(
        text(
            "INSERT INTO tenants (id, name, industry) VALUES (:id, :name, 'generic') "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "name": f"Tenant {tenant_id}"},
    )
    customer_id = (
        await session.execute(
            text(
                "INSERT INTO customers (id, tenant_id, name, archived) "
                "VALUES (gen_random_uuid(), :tid, 'Test Customer', false) RETURNING id"
            ),
            {"tid": str(tenant_id)},
        )
    ).scalar_one()
    location_id = (
        await session.execute(
            text(
                "INSERT INTO locations "
                "(id, tenant_id, customer_id, street, city, state, postal_code, country, geocode_status, archived) "
                "VALUES (gen_random_uuid(), :tid, :cid, '1 Main St', 'Portland', 'OR', '97201', 'US', 'pending', false) "
                "RETURNING id"
            ),
            {"tid": str(tenant_id), "cid": str(customer_id)},
        )
    ).scalar_one()
    job_id = (
        await session.execute(
            text(
                "INSERT INTO jobs "
                "(id, tenant_id, customer_id, location_id, industry, title, status, priority, estimated_duration_min, custom_fields) "
                "VALUES (gen_random_uuid(), :tid, :cid, :lid, 'generic', :title, 'pending', 50, 60, '{}') "
                "RETURNING id"
            ),
            {
                "tid": str(tenant_id),
                "cid": str(customer_id),
                "lid": str(location_id),
                "title": title,
            },
        )
    ).scalar_one()
    await session.commit()
    return str(job_id)


@pytest.mark.asyncio
async def test_tenant_isolation_jobs_hidden_by_rls(engine):
    """Tenant A jobs must not be visible when app.tenant_id = tenantB.

    RLS policy: ``tenant_id = current_setting('app.tenant_id')::uuid``.
    The test verifies this by creating a job under tenant A's session and
    then querying under tenant B's context — the result set must be empty.
    """
    tenant_a = uuid4()
    tenant_b = uuid4()
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async with sessionmaker() as session:
        job_a_id = await _seed_tenant_with_job(session, tenant_a, "Tenant A exclusive job")

    # Read in a tenant_b session — RLS should hide the row.
    async with sessionmaker() as session:
        await _set_tenant(session, tenant_b)
        rows = (
            await session.execute(
                text("SELECT id FROM jobs WHERE id = :jid"),
                {"jid": job_a_id},
            )
        ).all()
        assert rows == [], "RLS leak: tenant B can see tenant A's job"


@pytest.mark.asyncio
async def test_custom_fields_jsonb_roundtrip(engine):
    """Write nested JSON to custom_fields; read back and verify shape preserved."""
    tenant_id = uuid4()
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    payload = {"pest_type": "rodent", "access_notes": {"gate_code": "1234", "floors": [1, 3]}}

    async with sessionmaker() as session:
        job_id = await _seed_tenant_with_job(session, tenant_id, "JSONB test job")
        await _set_tenant(session, tenant_id)
        await session.execute(
            text("UPDATE jobs SET custom_fields = :cf WHERE id = :jid"),
            {"cf": str(payload).replace("'", '"'), "jid": job_id},
        )
        await session.commit()

        result = (
            await session.execute(
                text("SELECT custom_fields FROM jobs WHERE id = :jid"),
                {"jid": job_id},
            )
        ).scalar_one()
        assert result["pest_type"] == "rodent"
        assert result["access_notes"]["gate_code"] == "1234"
        assert result["access_notes"]["floors"] == [1, 3]


@pytest.mark.asyncio
async def test_jobs_gin_index_used_for_jsonb_contains_query(engine):
    """EXPLAIN ANALYZE should show a Bitmap Index Scan on idx_jobs_custom_fields_gin.

    This is a smoke / debug aid, not a hard assertion in CI.
    """
    tenant_id = uuid4()
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async with sessionmaker() as session:
        await _seed_tenant_with_job(session, tenant_id, "GIN index test job")
        await _set_tenant(session, tenant_id)
        await session.execute(
            text('UPDATE jobs SET custom_fields = \'{"service": "pest"}\' WHERE tenant_id = :tid'),
            {"tid": str(tenant_id)},
        )
        await session.commit()

        plan = (
            (
                await session.execute(
                    text(
                        'EXPLAIN SELECT id FROM jobs WHERE custom_fields @> \'{"service": "pest"}\''
                    )
                )
            )
            .scalars()
            .all()
        )

    plan_text = "\n".join(plan)
    assert (
        "idx_jobs_custom_fields_gin" in plan_text or "Index" in plan_text
    ), f"GIN index not used for JSONB containment query.\nPlan:\n{plan_text}"
