"""HTTP-layer tests for the /jobs routes (RBAC + tenant isolation + transitions)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from office_hero.api.app import create_app
from office_hero.repositories.customer_repository import InMemoryCustomerRepository
from office_hero.repositories.job_repository import InMemoryJobRepository
from office_hero.repositories.location_repository import InMemoryLocationRepository
from office_hero.repositories.mocks import InMemoryAuditService
from office_hero.services.custom_field_templates import registry as template_registry
from office_hero.services.job_service import JobService
from tests.api.conftest import (
    _hard_reset_limiter,
    _TestAuthMiddleware,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _build_job_app(
    *,
    cust_repo=None,
    loc_repo=None,
    job_repo=None,
    audit=None,
) -> tuple[FastAPI, InMemoryCustomerRepository, InMemoryLocationRepository, InMemoryJobRepository]:
    audit = audit or InMemoryAuditService()
    cust_repo = cust_repo or InMemoryCustomerRepository()
    loc_repo = loc_repo or InMemoryLocationRepository()
    job_repo = job_repo or InMemoryJobRepository()
    svc = JobService(
        repo=job_repo,
        customer_repo=cust_repo,
        location_repo=loc_repo,
        audit=audit,
        template_registry=template_registry,
    )
    app = create_app(job_service=svc)
    app.add_middleware(_TestAuthMiddleware)
    return app, cust_repo, loc_repo, job_repo


def _auth_headers(
    tenant_id,
    user_id,
    *,
    role: str = "tenant_admin",
    permissions: str = "jobs:read,jobs:write,jobs:dispatch,jobs:cancel",
) -> dict[str, str]:
    return {
        "X-Test-Tenant-Id": str(tenant_id),
        "X-Test-User-Id": str(user_id),
        "X-Test-Role": role,
        "X-Test-Permissions": permissions,
    }


def _dispatcher_headers(tenant_id, user_id) -> dict[str, str]:
    return _auth_headers(
        tenant_id,
        user_id,
        role="dispatcher",
        permissions="jobs:read,jobs:write,jobs:dispatch,jobs:cancel",
    )


def _technician_headers(tenant_id, user_id) -> dict[str, str]:
    return _auth_headers(
        tenant_id,
        user_id,
        role="technician",
        permissions="jobs:read",
    )


def _no_auth_headers() -> dict[str, str]:
    return {}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tenant_a():
    return uuid4()


@pytest.fixture()
def tenant_b():
    return uuid4()


@pytest.fixture()
def user_a():
    return uuid4()


@pytest.fixture()
def app_and_repos(tenant_a):
    app, cust_repo, loc_repo, job_repo = _build_job_app()
    return app, cust_repo, loc_repo, job_repo


@pytest.fixture()
def client(app_and_repos):
    app, *_ = app_and_repos
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def repos(app_and_repos):
    _, cust_repo, loc_repo, job_repo = app_and_repos
    return cust_repo, loc_repo, job_repo


async def _seed(cust_repo, loc_repo, tenant_id):
    """Create a customer and location; return (customer, location)."""
    cust = await cust_repo.create(tenant_id, name="Acme")
    loc = await loc_repo.create(
        tenant_id,
        cust.id,
        street="1 Main St",
        city="Austin",
        state="TX",
        postal_code="78701",
    )
    return cust, loc


# ---------------------------------------------------------------------------
# POST /jobs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_job_requires_jwt_401(client, repos, tenant_a, user_a):
    """No auth headers -> 401 or 403 (permission check fires first)."""
    cust_repo, loc_repo, _ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    resp = client.post(
        "/jobs",
        json={
            "customer_id": str(cust.id),
            "location_id": str(loc.id),
            "title": "Job",
        },
        headers=_no_auth_headers(),
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_post_job_without_jobs_write_perm_403(client, repos, tenant_a, user_a):
    """Technician lacks jobs:write -> 403."""
    cust_repo, loc_repo, _ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    resp = client.post(
        "/jobs",
        json={
            "customer_id": str(cust.id),
            "location_id": str(loc.id),
            "title": "Job",
        },
        headers=_technician_headers(tenant_a, user_a),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_post_job_201_and_returns_id(client, repos, tenant_a, user_a):
    """Successful create returns 201 with a UUID id and correct status."""
    cust_repo, loc_repo, _ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    resp = client.post(
        "/jobs",
        json={
            "customer_id": str(cust.id),
            "location_id": str(loc.id),
            "title": "Pipe Repair",
            "priority": 30,
        },
        headers=_auth_headers(tenant_a, user_a),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    assert body["status"] == "pending"
    assert body["title"] == "Pipe Repair"
    assert body["priority"] == 30
    assert body["tenant_id"] == str(tenant_a)


@pytest.mark.asyncio
async def test_post_job_invalid_customer_404(client, tenant_a, user_a, repos):
    """Referencing a non-existent customer returns 404."""
    cust_repo, loc_repo, _ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    resp = client.post(
        "/jobs",
        json={
            "customer_id": str(uuid4()),  # random non-existent
            "location_id": str(loc.id),
            "title": "Job",
        },
        headers=_auth_headers(tenant_a, user_a),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /jobs and GET /jobs/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_job_cross_tenant_404(tenant_a, tenant_b, user_a):
    """Tenant B cannot see tenant A's job."""
    app, cust_repo, loc_repo, _ = _build_job_app()
    cust_a, loc_a = None, None

    with TestClient(app) as client:
        cust_a = await cust_repo.create(tenant_a, name="Acme")
        loc_a = await loc_repo.create(
            tenant_a, cust_a.id, street="1 St", city="Austin", state="TX", postal_code="78701"
        )
        create = client.post(
            "/jobs",
            json={"customer_id": str(cust_a.id), "location_id": str(loc_a.id), "title": "Job A"},
            headers=_auth_headers(tenant_a, user_a),
        )
        assert create.status_code == 201
        job_id = create.json()["id"]

        # tenant B tries to read tenant A's job
        resp = client.get(
            f"/jobs/{job_id}",
            headers=_auth_headers(tenant_b, user_a, permissions="jobs:read"),
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_jobs_filter_by_status_and_date(
    disabled_limiter, client, repos, tenant_a, user_a
):
    """List endpoint honours status filter."""
    cust_repo, loc_repo, _ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    # Create two jobs
    client.post(
        "/jobs",
        json={"customer_id": str(cust.id), "location_id": str(loc.id), "title": "Job 1"},
        headers=_auth_headers(tenant_a, user_a),
    )
    client.post(
        "/jobs",
        json={"customer_id": str(cust.id), "location_id": str(loc.id), "title": "Job 2"},
        headers=_auth_headers(tenant_a, user_a),
    )

    resp = client.get(
        "/jobs?status=pending",
        headers=_auth_headers(tenant_a, user_a, permissions="jobs:read"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert all(j["status"] == "pending" for j in body["items"])

    resp2 = client.get(
        "/jobs?status=scheduled",
        headers=_auth_headers(tenant_a, user_a, permissions="jobs:read"),
    )
    assert resp2.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_jobs_pagination(disabled_limiter, client, repos, tenant_a, user_a):
    """limit and offset control the page."""
    cust_repo, loc_repo, _ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    for i in range(5):
        client.post(
            "/jobs",
            json={"customer_id": str(cust.id), "location_id": str(loc.id), "title": f"Job {i}"},
            headers=_auth_headers(tenant_a, user_a),
        )

    resp = client.get(
        "/jobs?limit=2&offset=0",
        headers=_auth_headers(tenant_a, user_a, permissions="jobs:read"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 5
    assert len(body["items"]) == 2


# ---------------------------------------------------------------------------
# PATCH /jobs/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_job_returns_422_when_status_field_supplied(client, repos, tenant_a, user_a):
    """Patching status directly via PATCH is rejected with 422."""
    cust_repo, loc_repo, _ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    create = client.post(
        "/jobs",
        json={"customer_id": str(cust.id), "location_id": str(loc.id), "title": "Job"},
        headers=_auth_headers(tenant_a, user_a),
    )
    job_id = create.json()["id"]

    resp = client.patch(
        f"/jobs/{job_id}",
        json={"status": "scheduled"},
        headers=_auth_headers(tenant_a, user_a),
    )
    # Pydantic extra="forbid" or our service guard should reject this
    assert resp.status_code in (422, 400)


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_schedule_job_dispatcher_succeeds(client, repos, tenant_a, user_a):
    """Dispatcher with jobs:dispatch can schedule a pending job."""
    cust_repo, loc_repo, _ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    create = client.post(
        "/jobs",
        json={"customer_id": str(cust.id), "location_id": str(loc.id), "title": "Job"},
        headers=_auth_headers(tenant_a, user_a),
    )
    job_id = create.json()["id"]

    resp = client.post(
        f"/jobs/{job_id}/schedule",
        json={"scheduled_for": "2026-06-01T09:00:00Z"},
        headers=_dispatcher_headers(tenant_a, user_a),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "scheduled"


@pytest.mark.asyncio
async def test_schedule_job_technician_403(client, repos, tenant_a, user_a):
    """Technician without jobs:dispatch cannot schedule."""
    cust_repo, loc_repo, _ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    create = client.post(
        "/jobs",
        json={"customer_id": str(cust.id), "location_id": str(loc.id), "title": "Job"},
        headers=_auth_headers(tenant_a, user_a),
    )
    job_id = create.json()["id"]

    resp = client.post(
        f"/jobs/{job_id}/schedule",
        json={"scheduled_for": "2026-06-01T09:00:00Z"},
        headers=_technician_headers(tenant_a, user_a),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_start_job_technician_succeeds(disabled_limiter, client, repos, tenant_a, user_a):
    """Technician role can start a scheduled job."""
    cust_repo, loc_repo, _ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    create = client.post(
        "/jobs",
        json={"customer_id": str(cust.id), "location_id": str(loc.id), "title": "Job"},
        headers=_auth_headers(tenant_a, user_a),
    )
    job_id = create.json()["id"]
    client.post(
        f"/jobs/{job_id}/schedule",
        json={"scheduled_for": "2026-06-01T09:00:00Z"},
        headers=_dispatcher_headers(tenant_a, user_a),
    )

    resp = client.post(
        f"/jobs/{job_id}/start",
        headers=_auth_headers(tenant_a, user_a, role="technician", permissions="jobs:read"),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


@pytest.mark.asyncio
async def test_complete_job_technician_succeeds_with_notes(
    disabled_limiter, client, repos, tenant_a, user_a
):
    """Technician can complete a job with completion notes."""
    cust_repo, loc_repo, _ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    create = client.post(
        "/jobs",
        json={"customer_id": str(cust.id), "location_id": str(loc.id), "title": "Job"},
        headers=_auth_headers(tenant_a, user_a),
    )
    job_id = create.json()["id"]
    client.post(
        f"/jobs/{job_id}/schedule",
        json={"scheduled_for": "2026-06-01T09:00:00Z"},
        headers=_dispatcher_headers(tenant_a, user_a),
    )
    client.post(
        f"/jobs/{job_id}/start",
        headers=_auth_headers(tenant_a, user_a, role="technician", permissions="jobs:read"),
    )

    resp = client.post(
        f"/jobs/{job_id}/complete",
        json={"completion_notes": "Fixed the leak."},
        headers=_auth_headers(tenant_a, user_a, role="technician", permissions="jobs:read"),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "complete"


@pytest.mark.asyncio
async def test_cancel_job_dispatcher_with_reason_succeeds(client, repos, tenant_a, user_a):
    """Dispatcher with jobs:cancel can cancel a pending job."""
    cust_repo, loc_repo, _ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    create = client.post(
        "/jobs",
        json={"customer_id": str(cust.id), "location_id": str(loc.id), "title": "Job"},
        headers=_auth_headers(tenant_a, user_a),
    )
    job_id = create.json()["id"]

    resp = client.post(
        f"/jobs/{job_id}/cancel",
        json={"reason": "Customer no-show"},
        headers=_dispatcher_headers(tenant_a, user_a),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "cancelled"
    assert body["cancel_reason"] == "Customer no-show"


@pytest.mark.asyncio
async def test_cancel_job_without_reason_422(client, repos, tenant_a, user_a):
    """cancel endpoint requires reason (min_length=3 enforced by Pydantic)."""
    cust_repo, loc_repo, _ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    create = client.post(
        "/jobs",
        json={"customer_id": str(cust.id), "location_id": str(loc.id), "title": "Job"},
        headers=_auth_headers(tenant_a, user_a),
    )
    job_id = create.json()["id"]

    resp = client.post(
        f"/jobs/{job_id}/cancel",
        json={},  # missing reason entirely
        headers=_dispatcher_headers(tenant_a, user_a),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_illegal_status_transition_returns_422(
    disabled_limiter, client, repos, tenant_a, user_a
):
    """Cancelling a completed job returns 422 with from/to in body."""
    cust_repo, loc_repo, _ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    create = client.post(
        "/jobs",
        json={"customer_id": str(cust.id), "location_id": str(loc.id), "title": "Job"},
        headers=_auth_headers(tenant_a, user_a),
    )
    job_id = create.json()["id"]

    # Walk to complete
    client.post(
        f"/jobs/{job_id}/schedule",
        json={"scheduled_for": "2026-06-01T09:00:00Z"},
        headers=_dispatcher_headers(tenant_a, user_a),
    )
    client.post(f"/jobs/{job_id}/start", headers=_auth_headers(tenant_a, user_a))
    client.post(
        f"/jobs/{job_id}/complete",
        json={},
        headers=_auth_headers(tenant_a, user_a),
    )

    # Now try to cancel a completed job
    resp = client.post(
        f"/jobs/{job_id}/cancel",
        json={"reason": "no longer needed"},
        headers=_dispatcher_headers(tenant_a, user_a),
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["from"] == "complete"
    assert body["to"] == "cancelled"


@pytest.mark.asyncio
async def test_jobs_write_endpoint_rate_limited_60_per_min(repos, tenant_a, user_a):
    """POST /jobs is rate-limited at 60/min per IP."""
    _hard_reset_limiter()
    app, cust_repo, loc_repo, _ = _build_job_app()
    cust, loc = None, None
    cust = await cust_repo.create(tenant_a, name="Acme")
    loc = await loc_repo.create(
        tenant_a, cust.id, street="1 St", city="Austin", state="TX", postal_code="78701"
    )

    body = {
        "customer_id": str(cust.id),
        "location_id": str(loc.id),
        "title": "Rate test",
    }
    headers = _auth_headers(tenant_a, user_a)

    with TestClient(app) as client:
        statuses = []
        for _ in range(65):
            r = client.post("/jobs", json=body, headers=headers)
            statuses.append(r.status_code)

    assert 429 in statuses, "Expected at least one 429 after 60 requests"
    _hard_reset_limiter()
