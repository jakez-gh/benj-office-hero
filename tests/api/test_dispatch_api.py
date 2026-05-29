"""HTTP-layer tests for POST /jobs/{job_id}/dispatch (Slice 14)."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from office_hero.api.app import create_app
from office_hero.api.limiter import limiter
from office_hero.repositories.job_repository import InMemoryJobRepository
from office_hero.repositories.vehicle_repository import InMemoryVehicleRepository
from office_hero.services.job_dispatch_service import JobDispatchService


class _DispatchTestAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.tenant_id = request.headers.get("X-Test-Tenant-Id")
        request.state.user_id = request.headers.get("X-Test-User-Id")
        request.state.role = request.headers.get("X-Test-Role", "dispatcher")
        perms_raw = request.headers.get("X-Test-Permissions", "job:write,vehicle:read")
        request.state.permissions = [p.strip() for p in perms_raw.split(",") if p.strip()]
        return await call_next(request)


# ---------------------------------------------------------------------------
# Rate-limiter isolation: give each test its own bucket
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Isolate rate-limit counters per test (avoid 429s from shared IP bucket)."""
    test_key = str(uuid4())
    saved: list[tuple] = []
    for limits in limiter._route_limits.values():
        for lim in limits:
            saved.append((lim, lim.key_func))
            lim.key_func = lambda *_a, **_k: test_key
    yield
    for lim, orig in saved:
        lim.key_func = orig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _auth_headers(tenant_id, user_id, *, perms: str = "job:write,vehicle:read") -> dict[str, str]:
    return {
        "X-Test-Tenant-Id": str(tenant_id),
        "X-Test-User-Id": str(user_id),
        "X-Test-Role": "dispatcher",
        "X-Test-Permissions": perms,
    }


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture()
def tenant_id() -> UUID:
    return uuid4()


@pytest.fixture()
def user_id() -> UUID:
    return uuid4()


@pytest.fixture()
def job_repo() -> InMemoryJobRepository:
    return InMemoryJobRepository()


@pytest.fixture()
def v_repo() -> InMemoryVehicleRepository:
    return InMemoryVehicleRepository()


@pytest.fixture()
def dispatch_service(job_repo, v_repo) -> JobDispatchService:
    return JobDispatchService(job_repo=job_repo, vehicle_repo=v_repo)


@pytest.fixture()
def app(dispatch_service) -> FastAPI:
    saved = dict(limiter._route_limits)
    limiter._route_limits.clear()
    a = create_app(job_dispatch_service=dispatch_service)
    a.add_middleware(_DispatchTestAuthMiddleware)
    yield a
    limiter._route_limits.clear()
    limiter._route_limits.update(saved)


@pytest.fixture()
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def pending_job(job_repo, tenant_id, user_id):
    """A pending job seeded into the in-memory job repository."""

    async def _create():
        return await job_repo.create(
            tenant_id,
            customer_id=uuid4(),
            location_id=uuid4(),
            industry="plumbing",
            title="Fix leaking pipe",
            description=None,
            priority=50,
            service_type="Drain cleaning",
            requested_at=None,
            requested_until=None,
            estimated_duration_min=60,
            custom_fields={},
            created_by_user_id=user_id,
        )

    return _run(_create())


@pytest.fixture()
def active_vehicle(v_repo, tenant_id):
    """An active vehicle seeded into the in-memory vehicle repository."""

    async def _create():
        return await v_repo.create(
            tenant_id,
            license_plate="ABC-123",
            nickname="Van #1",
            make="Ford",
            model="Transit",
            year=2022,
        )

    return _run(_create())


WINDOW_START = datetime(2027, 6, 1, 9, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_dispatch_success(client, tenant_id, user_id, pending_job, active_vehicle):
    """Successful dispatch returns 200 with scheduled status and vehicle assigned."""
    resp = client.post(
        f"/jobs/{pending_job.id}/dispatch",
        json={
            "vehicle_id": str(active_vehicle.id),
            "scheduled_for": WINDOW_START.isoformat(),
        },
        headers=_auth_headers(tenant_id, user_id),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "scheduled"
    assert data["assigned_vehicle_id"] == str(active_vehicle.id)
    assert "scheduled_for" in data
    assert data["id"] == str(pending_job.id)


def test_dispatch_job_not_found_404(client, tenant_id, user_id, active_vehicle):
    """Non-existent job returns 404."""
    resp = client.post(
        f"/jobs/{uuid4()}/dispatch",
        json={
            "vehicle_id": str(active_vehicle.id),
            "scheduled_for": WINDOW_START.isoformat(),
        },
        headers=_auth_headers(tenant_id, user_id),
    )
    assert resp.status_code == 404


def test_dispatch_vehicle_not_found_404(client, tenant_id, user_id, pending_job):
    """Non-existent vehicle returns 404."""
    resp = client.post(
        f"/jobs/{pending_job.id}/dispatch",
        json={
            "vehicle_id": str(uuid4()),
            "scheduled_for": WINDOW_START.isoformat(),
        },
        headers=_auth_headers(tenant_id, user_id),
    )
    assert resp.status_code == 404


def test_dispatch_invalid_transition_409(client, tenant_id, user_id, active_vehicle, job_repo):
    """Dispatching an already-scheduled job returns 409."""

    async def _create_scheduled():
        job = await job_repo.create(
            tenant_id,
            customer_id=uuid4(),
            location_id=uuid4(),
            industry="plumbing",
            title="Already scheduled",
            description=None,
            priority=50,
            service_type=None,
            requested_at=None,
            requested_until=None,
            estimated_duration_min=60,
            custom_fields={},
            created_by_user_id=uuid4(),
        )
        # Force status to scheduled
        return await job_repo.update_fields(job.id, tenant_id, status="scheduled")

    scheduled_job = _run(_create_scheduled())
    resp = client.post(
        f"/jobs/{scheduled_job.id}/dispatch",
        json={
            "vehicle_id": str(active_vehicle.id),
            "scheduled_for": WINDOW_START.isoformat(),
        },
        headers=_auth_headers(tenant_id, user_id),
    )
    assert resp.status_code == 409


def test_dispatch_vehicle_already_booked_409(
    client, tenant_id, user_id, job_repo, v_repo, active_vehicle
):
    """Second dispatch for the same vehicle/time-window returns 409."""

    async def _create_and_assign():
        job1 = await job_repo.create(
            tenant_id,
            customer_id=uuid4(),
            location_id=uuid4(),
            industry="plumbing",
            title="Job 1",
            description=None,
            priority=50,
            service_type=None,
            requested_at=None,
            requested_until=None,
            estimated_duration_min=60,
            custom_fields={},
            created_by_user_id=uuid4(),
        )
        job2 = await job_repo.create(
            tenant_id,
            customer_id=uuid4(),
            location_id=uuid4(),
            industry="plumbing",
            title="Job 2",
            description=None,
            priority=50,
            service_type=None,
            requested_at=None,
            requested_until=None,
            estimated_duration_min=60,
            custom_fields={},
            created_by_user_id=uuid4(),
        )
        # Mark job1 as already assigned to the vehicle at the same slot
        await job_repo.update_fields(
            job1.id,
            tenant_id,
            status="scheduled",
            assigned_vehicle_id=active_vehicle.id,
            scheduled_for=WINDOW_START,
        )
        return job2

    job2 = _run(_create_and_assign())
    resp = client.post(
        f"/jobs/{job2.id}/dispatch",
        json={
            "vehicle_id": str(active_vehicle.id),
            "scheduled_for": WINDOW_START.isoformat(),
        },
        headers=_auth_headers(tenant_id, user_id),
    )
    assert resp.status_code == 409


def test_dispatch_missing_job_write_permission_403(
    client, tenant_id, user_id, pending_job, active_vehicle
):
    """Missing job:write permission returns 403."""
    resp = client.post(
        f"/jobs/{pending_job.id}/dispatch",
        json={
            "vehicle_id": str(active_vehicle.id),
            "scheduled_for": WINDOW_START.isoformat(),
        },
        headers=_auth_headers(tenant_id, user_id, perms="vehicle:read"),
    )
    assert resp.status_code == 403


def test_dispatch_missing_vehicle_read_permission_403(
    client, tenant_id, user_id, pending_job, active_vehicle
):
    """Missing vehicle:read permission returns 403."""
    resp = client.post(
        f"/jobs/{pending_job.id}/dispatch",
        json={
            "vehicle_id": str(active_vehicle.id),
            "scheduled_for": WINDOW_START.isoformat(),
        },
        headers=_auth_headers(tenant_id, user_id, perms="job:write"),
    )
    assert resp.status_code == 403


def test_dispatch_cross_tenant_vehicle_404(client, tenant_id, user_id, pending_job, v_repo):
    """Vehicle belonging to a different tenant is not found — returns 404."""

    async def _create_other_tenant_vehicle():
        other_tenant = uuid4()
        return await v_repo.create(
            other_tenant,
            license_plate="XYZ-999",
            nickname="Other Tenant Van",
            make="Ford",
            model="Transit",
            year=2021,
        )

    other_vehicle = _run(_create_other_tenant_vehicle())
    resp = client.post(
        f"/jobs/{pending_job.id}/dispatch",
        json={
            "vehicle_id": str(other_vehicle.id),
            "scheduled_for": WINDOW_START.isoformat(),
        },
        headers=_auth_headers(tenant_id, user_id),
    )
    assert resp.status_code == 404


def test_dispatch_naive_datetime_422(client, tenant_id, user_id, pending_job, active_vehicle):
    """Naive (timezone-unaware) scheduled_for is rejected with 422."""
    resp = client.post(
        f"/jobs/{pending_job.id}/dispatch",
        json={
            "vehicle_id": str(active_vehicle.id),
            "scheduled_for": "2027-06-01T09:00:00",  # no timezone
        },
        headers=_auth_headers(tenant_id, user_id),
    )
    assert resp.status_code == 422
