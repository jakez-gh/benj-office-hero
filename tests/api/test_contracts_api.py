"""HTTP-layer tests for the /contracts routes (RBAC + tenant isolation + generation)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from office_hero.api.app import create_app
from office_hero.repositories.contract_repository import InMemoryContractRepository
from office_hero.repositories.customer_repository import InMemoryCustomerRepository
from office_hero.repositories.job_repository import InMemoryJobRepository
from office_hero.repositories.location_repository import InMemoryLocationRepository
from office_hero.repositories.mocks import InMemoryAuditService
from office_hero.services.contract_service import ContractService
from office_hero.services.custom_field_templates import registry as template_registry
from tests.api.conftest import _TestAuthMiddleware

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _build_contract_app() -> tuple[
    FastAPI,
    InMemoryCustomerRepository,
    InMemoryLocationRepository,
    InMemoryContractRepository,
    InMemoryJobRepository,
]:
    audit = InMemoryAuditService()
    cust_repo = InMemoryCustomerRepository()
    loc_repo = InMemoryLocationRepository()
    contract_repo = InMemoryContractRepository()
    job_repo = InMemoryJobRepository()
    svc = ContractService(
        repo=contract_repo,
        customer_repo=cust_repo,
        location_repo=loc_repo,
        job_repo=job_repo,
        audit=audit,
        template_registry=template_registry,
    )
    app = create_app(contract_service=svc)
    app.add_middleware(_TestAuthMiddleware)
    return app, cust_repo, loc_repo, contract_repo, job_repo


def _auth_headers(
    tenant_id,
    user_id,
    *,
    role: str = "tenant_admin",
    permissions: str = "contracts:read,contracts:write,jobs:write",
) -> dict[str, str]:
    return {
        "X-Test-Tenant-Id": str(tenant_id),
        "X-Test-User-Id": str(user_id),
        "X-Test-Role": role,
        "X-Test-Permissions": permissions,
    }


def _sales_headers(tenant_id, user_id) -> dict[str, str]:
    """Sales can enter Contracts (per spec RBAC table) but cannot create Jobs."""
    return _auth_headers(
        tenant_id,
        user_id,
        role="sales",
        permissions="contracts:read,contracts:write",
    )


def _technician_headers(tenant_id, user_id) -> dict[str, str]:
    """Technician has no contracts permissions at all."""
    return _auth_headers(
        tenant_id,
        user_id,
        role="technician",
        permissions="jobs:read",
    )


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
def app_and_repos():
    """Build the app with only this app's rate limits active.

    Every ``create_app()`` in earlier test files re-registered limits under
    the same endpoint names (sharing storage buckets), so clear
    ``limiter._route_limits`` first and restore it afterwards — see the
    project git rules and tests/integration/test_golden_path.py.
    """
    from office_hero.api.limiter import limiter

    saved_route_limits = dict(limiter._route_limits)
    limiter._route_limits.clear()
    try:
        yield _build_contract_app()
    finally:
        limiter._route_limits.clear()
        limiter._route_limits.update(saved_route_limits)


@pytest.fixture()
def client(app_and_repos):
    app, *_ = app_and_repos
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def repos(app_and_repos):
    _, cust_repo, loc_repo, contract_repo, job_repo = app_and_repos
    return cust_repo, loc_repo, contract_repo, job_repo


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


def _contract_body(cust, loc, **overrides):
    body = {
        "customer_id": str(cust.id),
        "location_id": str(loc.id),
        "title": "Quarterly pest plan",
        "frequency": "quarterly",
        "start_date": "2026-06-01",
    }
    body.update(overrides)
    return body


# ---------------------------------------------------------------------------
# POST /contracts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_contract_requires_auth(client, repos, tenant_a):
    cust_repo, loc_repo, *_ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    resp = client.post("/contracts", json=_contract_body(cust, loc), headers={})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_post_contract_without_write_perm_403(client, repos, tenant_a, user_a):
    cust_repo, loc_repo, *_ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    resp = client.post(
        "/contracts",
        json=_contract_body(cust, loc),
        headers=_technician_headers(tenant_a, user_a),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_post_contract_201_as_tenant_admin(client, repos, tenant_a, user_a):
    cust_repo, loc_repo, *_ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    resp = client.post(
        "/contracts",
        json=_contract_body(cust, loc),
        headers=_auth_headers(tenant_a, user_a),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "active"
    assert body["next_due"] == "2026-06-01"
    assert body["frequency"] == "quarterly"


@pytest.mark.asyncio
async def test_post_contract_201_as_sales_role(client, repos, tenant_a, user_a):
    """Sales role can enter contracts — the spec's core Sales workflow."""
    cust_repo, loc_repo, *_ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    resp = client.post(
        "/contracts",
        json=_contract_body(cust, loc),
        headers=_sales_headers(tenant_a, user_a),
    )
    assert resp.status_code == 201, resp.text


@pytest.mark.asyncio
async def test_post_contract_unknown_customer_404(client, repos, tenant_a, user_a):
    cust_repo, loc_repo, *_ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    body = _contract_body(cust, loc, customer_id=str(uuid4()))
    resp = client.post("/contracts", json=body, headers=_auth_headers(tenant_a, user_a))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_post_contract_invalid_frequency_422(client, repos, tenant_a, user_a):
    cust_repo, loc_repo, *_ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    body = _contract_body(cust, loc, frequency="fortnightly")
    resp = client.post("/contracts", json=body, headers=_auth_headers(tenant_a, user_a))
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_contract_end_before_start_422(client, repos, tenant_a, user_a):
    cust_repo, loc_repo, *_ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    body = _contract_body(cust, loc, end_date="2026-01-01")
    resp = client.post("/contracts", json=body, headers=_auth_headers(tenant_a, user_a))
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_contract_extra_field_422(client, repos, tenant_a, user_a):
    """ConfigDict(extra='forbid') rejects unknown fields."""
    cust_repo, loc_repo, *_ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    body = _contract_body(cust, loc, nonsense_field=True)
    resp = client.post("/contracts", json=body, headers=_auth_headers(tenant_a, user_a))
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /contracts + /contracts/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_contracts_filters_by_status(client, repos, tenant_a, user_a):
    cust_repo, loc_repo, *_ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    headers = _auth_headers(tenant_a, user_a)
    first = client.post("/contracts", json=_contract_body(cust, loc), headers=headers).json()
    client.post(
        "/contracts",
        json=_contract_body(cust, loc, title="Second plan"),
        headers=headers,
    )
    client.post(f"/contracts/{first['id']}/pause", headers=headers)

    resp = client.get("/contracts", params={"status": "active"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Second plan"


@pytest.mark.asyncio
async def test_list_contracts_pagination(client, repos, tenant_a, user_a):
    cust_repo, loc_repo, *_ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    headers = _auth_headers(tenant_a, user_a)
    for i in range(3):
        client.post(
            "/contracts",
            json=_contract_body(cust, loc, title=f"Plan {i}"),
            headers=headers,
        )

    resp = client.get("/contracts", params={"limit": 2, "offset": 2}, headers=headers)
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 1


@pytest.mark.asyncio
async def test_get_contract_cross_tenant_404(client, repos, tenant_a, tenant_b, user_a):
    cust_repo, loc_repo, *_ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    created = client.post(
        "/contracts",
        json=_contract_body(cust, loc),
        headers=_auth_headers(tenant_a, user_a),
    ).json()

    resp = client.get(f"/contracts/{created['id']}", headers=_auth_headers(tenant_b, user_a))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH + lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_contract_status_field_rejected(client, repos, tenant_a, user_a):
    cust_repo, loc_repo, *_ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    headers = _auth_headers(tenant_a, user_a)
    created = client.post("/contracts", json=_contract_body(cust, loc), headers=headers).json()

    resp = client.patch(f"/contracts/{created['id']}", json={"status": "ended"}, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_patch_contract_explicit_null_rejected_422(client, repos, tenant_a, user_a):
    """Explicit JSON null on a NOT NULL field must 422 and leave state intact."""
    cust_repo, loc_repo, *_ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    headers = _auth_headers(tenant_a, user_a)
    created = client.post("/contracts", json=_contract_body(cust, loc), headers=headers).json()

    resp = client.patch(f"/contracts/{created['id']}", json={"next_due": None}, headers=headers)
    assert resp.status_code == 422

    # The contract list must still be readable (no poisoned row).
    listing = client.get("/contracts", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["items"][0]["next_due"] == "2026-06-01"


@pytest.mark.asyncio
async def test_patch_contract_next_due(client, repos, tenant_a, user_a):
    cust_repo, loc_repo, *_ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    headers = _auth_headers(tenant_a, user_a)
    created = client.post("/contracts", json=_contract_body(cust, loc), headers=headers).json()

    resp = client.patch(
        f"/contracts/{created['id']}", json={"next_due": "2026-09-01"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["next_due"] == "2026-09-01"


@pytest.mark.asyncio
async def test_pause_resume_end_lifecycle(client, repos, tenant_a, user_a):
    cust_repo, loc_repo, *_ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    headers = _auth_headers(tenant_a, user_a)
    created = client.post("/contracts", json=_contract_body(cust, loc), headers=headers).json()
    cid = created["id"]

    assert client.post(f"/contracts/{cid}/pause", headers=headers).json()["status"] == "paused"
    assert client.post(f"/contracts/{cid}/resume", headers=headers).json()["status"] == "active"
    ended = client.post(
        f"/contracts/{cid}/end", json={"reason": "customer moved"}, headers=headers
    ).json()
    assert ended["status"] == "ended"
    assert ended["end_reason"] == "customer moved"

    # Terminal: any further transition is 422.
    assert client.post(f"/contracts/{cid}/resume", headers=headers).status_code == 422


# ---------------------------------------------------------------------------
# POST /contracts/generate-jobs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_jobs_creates_jobs_and_is_idempotent(client, repos, tenant_a, user_a):
    cust_repo, loc_repo, *_ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    headers = _auth_headers(tenant_a, user_a)
    client.post("/contracts", json=_contract_body(cust, loc), headers=headers)

    first = client.post("/contracts/generate-jobs", json={"as_of": "2026-06-01"}, headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["count"] == 1
    assert first.json()["generated"][0]["status"] == "pending"

    second = client.post("/contracts/generate-jobs", json={"as_of": "2026-06-01"}, headers=headers)
    assert second.json()["count"] == 0


@pytest.mark.asyncio
async def test_generate_jobs_far_future_as_of_422(client, repos, tenant_a, user_a):
    """as_of beyond the 31-day horizon is rejected before any state changes."""
    cust_repo, loc_repo, *_ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    headers = _auth_headers(tenant_a, user_a)
    client.post("/contracts", json=_contract_body(cust, loc), headers=headers)

    resp = client.post("/contracts/generate-jobs", json={"as_of": "2030-01-01"}, headers=headers)
    assert resp.status_code == 422

    # Contract untouched — next generation at a sane date still works.
    listing = client.get("/contracts", headers=headers)
    assert listing.json()["items"][0]["next_due"] == "2026-06-01"


@pytest.mark.asyncio
async def test_generate_jobs_requires_jobs_write_in_addition_to_contracts_write(
    client, repos, tenant_a, user_a
):
    """Sales (contracts:write but no jobs:write) cannot run generation."""
    cust_repo, loc_repo, *_ = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    client.post(
        "/contracts",
        json=_contract_body(cust, loc),
        headers=_auth_headers(tenant_a, user_a),
    )

    resp = client.post(
        "/contracts/generate-jobs",
        json={"as_of": "2026-06-01"},
        headers=_sales_headers(tenant_a, user_a),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_generated_jobs_visible_via_jobs_repo(client, repos, tenant_a, user_a):
    """Generated jobs land in the shared job repository with contract provenance."""
    cust_repo, loc_repo, _, job_repo = repos
    cust, loc = await _seed(cust_repo, loc_repo, tenant_a)
    headers = _auth_headers(tenant_a, user_a)
    created = client.post("/contracts", json=_contract_body(cust, loc), headers=headers).json()

    client.post("/contracts/generate-jobs", json={"as_of": "2026-06-01"}, headers=headers)

    jobs, total = await job_repo.list(tenant_a)
    assert total == 1
    assert str(jobs[0].contract_id) == created["id"]
