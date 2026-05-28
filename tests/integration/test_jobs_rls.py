"""Integration tests for Job RLS and JSONB round-trip.

These tests require a live PostgreSQL database with ``DATABASE_URL`` set.
They are skipped automatically in CI when ``DATABASE_URL`` is absent so the
test suite still passes in the standard unit/API environment.

To run manually::

    DATABASE_URL=postgresql+asyncpg://... pytest tests/integration/test_jobs_rls.py -v
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set — skipping DB integration tests",
)

# ---------------------------------------------------------------------------
# The tests below only execute when DATABASE_URL is present.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tenant_isolation_jobs_hidden_by_rls(async_db_session_factory):
    """Tenant A jobs must not be visible when app.tenant_id = tenantB.

    RLS policy: ``tenant_id = current_setting('app.tenant_id')::uuid``.
    The test verifies this by creating a job under tenant A's session and
    then querying under tenant B's context — the result set must be empty.
    """
    # TODO: implement when integration test harness is wired in a future slice.
    pytest.xfail("Integration harness not yet wired — implement in a future slice.")


@pytest.mark.asyncio
async def test_custom_fields_jsonb_roundtrip(async_db_session_factory):
    """Write nested JSON to custom_fields; read back and verify shape preserved."""
    # TODO: implement when integration test harness is wired in a future slice.
    pytest.xfail("Integration harness not yet wired — implement in a future slice.")


@pytest.mark.asyncio
async def test_jobs_gin_index_used_for_jsonb_contains_query(async_db_session_factory):
    """EXPLAIN ANALYZE should show a Bitmap Index Scan on idx_jobs_custom_fields_gin.

    This is a smoke / debug aid, not a hard assertion in CI.
    """
    # TODO: implement when integration test harness is wired in a future slice.
    pytest.xfail("Integration harness not yet wired — implement in a future slice.")
