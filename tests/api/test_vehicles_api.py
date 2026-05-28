"""HTTP-layer tests for the /vehicles routes (RBAC + rate limiting)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, time
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from office_hero.api.app import create_app
from office_hero.api.limiter import limiter
from office_hero.core.crew_role import CrewRole
from office_hero.repositories.mocks import InMemoryAuditService
from office_hero.repositories.vehicle_crew_repository import (
    CrewMemberInput,
    InMemoryVehicleCrewRepository,
)
from office_hero.repositories.vehicle_repository import InMemoryVehicleRepository
from office_hero.services.vehicle_crew_service import VehicleCrewService
from office_hero.services.vehicle_service import VehicleService

# ---------------------------------------------------------------------------
# Shared auth middleware + helpers
# ---------------------------------------------------------------------------


class _VehicleTestAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.tenant_id = request.headers.get("X-Test-Tenant-Id")
        request.state.user_id = request.headers.get("X-Test-User-Id")
        request.state.role = request.headers.get("X-Test-Role", "tenant_admin")
        perms = request.headers.get("X-Test-Permissions", "vehicles:read,vehicles:write")
        request.state.permissions = [p.strip() for p in perms.split(",") if p.strip()]
        return await call_next(request)


def _reset_limiter() -> None:
    import contextlib

    limiter.reset()
    storage = getattr(getattr(limiter, "limiter", None), "storage", None)
    if storage and hasattr(storage, "reset"):
        with contextlib.suppress(Exception):
            storage.reset()
    for attr in ("storage", "events", "locks", "expirations"):
        bucket = getattr(storage, attr, None) if storage else None
        if hasattr(bucket, "clear"):
            with contextlib.suppress(Exception):
                bucket.clear()


def admin_headers(tenant_id, user_id) -> dict[str, str]:
    return {
        "X-Test-Tenant-Id": str(tenant_id),
        "X-Test-User-Id": str(user_id),
        "X-Test-Role": "tenant_admin",
        "X-Test-Permissions": "vehicles:read,vehicles:write",
    }


def dispatcher_headers(tenant_id, user_id) -> dict[str, str]:
    return {
        "X-Test-Tenant-Id": str(tenant_id),
        "X-Test-User-Id": str(user_id),
        "X-Test-Role": "dispatcher",
        "X-Test-Permissions": "vehicles:read",
    }


def technician_headers(tenant_id, user_id) -> dict[str, str]:
    return {
        "X-Test-Tenant-Id": str(tenant_id),
        "X-Test-User-Id": str(user_id),
        "X-Test-Role": "technician",
        "X-Test-Permissions": "",
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    _reset_limiter()
    yield
    _reset_limiter()


@pytest.fixture()
def tenant_a():
    return uuid4()


@pytest.fixture()
def user_a():
    return uuid4()


@pytest.fixture()
def audit():
    return InMemoryAuditService()


@pytest.fixture()
def v_repo():
    return InMemoryVehicleRepository()


@pytest.fixture()
def vc_repo():
    return InMemoryVehicleCrewRepository()


class _NoopUserRepo:
    async def get_by_id(self, user_id, tenant_id):
        return None


@pytest.fixture()
def vehicle_service(v_repo, vc_repo, audit):
    v_repo._crew_repo = vc_repo
    return VehicleService(repo=v_repo, audit=audit, crew_repo=vc_repo)


@pytest.fixture()
def crew_service(vc_repo, v_repo, audit):
    return VehicleCrewService(
        crew_repo=vc_repo,
        vehicle_repo=v_repo,
        user_repo=_NoopUserRepo(),
        audit=audit,
    )


@pytest.fixture()
def app(vehicle_service, crew_service) -> FastAPI:
    a = create_app(vehicle_service=vehicle_service, vehicle_crew_service=crew_service)
    a.add_middleware(_VehicleTestAuthMiddleware)
    return a


@pytest.fixture()
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_post_vehicle_requires_admin_role(client, tenant_a, user_a):
    """Dispatcher (non-admin/operator) must get 403 on POST /vehicles."""
    resp = client.post(
        "/vehicles",
        json={"license_plate": "DISP-001"},
        headers=dispatcher_headers(tenant_a, user_a),
    )
    assert resp.status_code == 403


def test_post_vehicle_201_returns_id(client, tenant_a, user_a):
    """Admin can create a vehicle; response includes the UUID."""
    resp = client.post(
        "/vehicles",
        json={"license_plate": "ADMIN-001", "make": "Ford", "year": 2022},
        headers=admin_headers(tenant_a, user_a),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["license_plate"] == "ADMIN-001"
    assert "id" in body
    assert body["tenant_id"] == str(tenant_a)


def test_get_vehicles_dispatcher_can_read(client, tenant_a, user_a):
    """Dispatcher can list vehicles (has vehicles:read)."""
    # First create one via admin
    client.post(
        "/vehicles",
        json={"license_plate": "READ-001"},
        headers=admin_headers(tenant_a, user_a),
    )
    resp = client.get(
        "/vehicles",
        headers=dispatcher_headers(tenant_a, user_a),
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


def test_get_vehicles_technician_403(client, tenant_a, user_a):
    """Technician lacks vehicles:read permission; expect 403."""
    resp = client.get(
        "/vehicles",
        headers=technician_headers(tenant_a, user_a),
    )
    assert resp.status_code == 403


def test_archive_vehicle_with_today_crew_409(client, tenant_a, user_a, vc_repo):
    """Archiving a vehicle that has a crew for today returns 409."""
    create_resp = client.post(
        "/vehicles",
        json={"license_plate": "CREW-VHCL"},
        headers=admin_headers(tenant_a, user_a),
    )
    vid = uuid4()
    # Inject a crew for today directly into vc_repo
    import asyncio

    vid = create_resp.json()["id"]
    from uuid import UUID

    vid_uuid = UUID(vid)

    async def _inject():
        await vc_repo.create(
            tenant_a,
            vehicle_id=vid_uuid,
            work_date=date.today(),
            shift_start=time(8, 0),
            shift_end=time(17, 0),
            notes=None,
            created_by_user_id=user_a,
            members=[CrewMemberInput(user_id=uuid4(), role_on_crew=CrewRole.LEAD)],
        )

    asyncio.get_event_loop().run_until_complete(_inject())

    resp = client.post(
        f"/vehicles/{vid}/archive",
        headers=admin_headers(tenant_a, user_a),
    )
    assert resp.status_code == 409


def test_vehicles_rate_limited_60_per_min(client, tenant_a, user_a):
    """More than 60 POST requests in a minute triggers 429."""
    limiter.enabled = True
    for i in range(60):
        client.post(
            "/vehicles",
            json={"license_plate": f"RL-{i:04d}"},
            headers=admin_headers(tenant_a, user_a),
        )
    resp = client.post(
        "/vehicles",
        json={"license_plate": "RL-9999"},
        headers=admin_headers(tenant_a, user_a),
    )
    assert resp.status_code == 429
