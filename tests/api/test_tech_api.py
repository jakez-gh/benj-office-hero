"""HTTP-layer tests for GET /vehicles/my-crew-today (Slice 22)."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, time
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from office_hero.api.app import create_app
from office_hero.api.limiter import limiter
from office_hero.repositories.vehicle_crew_repository import InMemoryVehicleCrewRepository
from office_hero.repositories.vehicle_repository import InMemoryVehicleRepository
from office_hero.services.vehicle_crew_service import VehicleCrewService


class _TechTestAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.tenant_id = request.headers.get("X-Test-Tenant-Id")
        request.state.user_id = request.headers.get("X-Test-User-Id")
        request.state.role = request.headers.get("X-Test-Role", "technician")
        perms_raw = request.headers.get("X-Test-Permissions", "vehicles:read")
        request.state.permissions = [p.strip() for p in perms_raw.split(",") if p.strip()]
        return await call_next(request)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    test_key = str(uuid4())
    saved: list[tuple] = []
    for limits in limiter._route_limits.values():
        for lim in limits:
            saved.append((lim, lim.key_func))
            lim.key_func = lambda *_a, **_k: test_key
    yield
    for lim, orig in saved:
        lim.key_func = orig


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture()
def tenant_id() -> UUID:
    return uuid4()


@pytest.fixture()
def user_id() -> UUID:
    return uuid4()


@pytest.fixture()
def v_repo() -> InMemoryVehicleRepository:
    return InMemoryVehicleRepository()


@pytest.fixture()
def crew_repo(v_repo) -> InMemoryVehicleCrewRepository:
    repo = InMemoryVehicleCrewRepository()
    v_repo._crew_repo = repo
    return repo


@pytest.fixture()
def crew_service(v_repo, crew_repo) -> VehicleCrewService:
    class _NoopUserRepo:
        async def get_by_id(self, user_id, tenant_id):
            return None

    from office_hero.repositories.mocks import InMemoryAuditService

    return VehicleCrewService(
        crew_repo=crew_repo,
        vehicle_repo=v_repo,
        user_repo=_NoopUserRepo(),
        audit=InMemoryAuditService(),
    )


@pytest.fixture()
def app(crew_service) -> FastAPI:
    saved = dict(limiter._route_limits)
    limiter._route_limits.clear()
    a = create_app(vehicle_crew_service=crew_service)
    a.add_middleware(_TechTestAuthMiddleware)
    yield a
    limiter._route_limits.clear()
    limiter._route_limits.update(saved)


@pytest.fixture()
def client(app) -> TestClient:
    with TestClient(app) as c:
        yield c


def _headers(tenant_id, user_id, *, perms: str = "vehicles:read") -> dict[str, str]:
    return {
        "X-Test-Tenant-Id": str(tenant_id),
        "X-Test-User-Id": str(user_id),
        "X-Test-Role": "technician",
        "X-Test-Permissions": perms,
    }


@pytest.fixture()
def vehicle(v_repo, tenant_id):
    async def _create():
        return await v_repo.create(
            tenant_id,
            license_plate="TRK-001",
            nickname="Tech Van",
            make="Ford",
            model="Transit",
            year=2023,
        )
    return _run(_create())


@pytest.fixture()
def crew_for_today(crew_repo, tenant_id, user_id, vehicle):
    today = datetime.now(UTC).date()

    async def _create():
        from office_hero.core.crew_role import CrewRole
        from office_hero.repositories.vehicle_crew_repository import CrewMemberInput

        return await crew_repo.create(
            tenant_id,
            vehicle_id=vehicle.id,
            work_date=today,
            shift_start=time(8, 0),
            shift_end=time(17, 0),
            notes=None,
            members=[CrewMemberInput(user_id=user_id, role_on_crew=CrewRole.LEAD)],
            created_by_user_id=user_id,
        )

    return _run(_create())


def test_my_crew_today_success(client, tenant_id, user_id, crew_for_today, vehicle):
    """Returns vehicle_id for a technician with a crew assignment today."""
    resp = client.get(
        "/vehicles/my-crew-today",
        headers=_headers(tenant_id, user_id),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["vehicle_id"] == str(vehicle.id)
    assert data["crew_id"] == str(crew_for_today.id)
    assert data["work_date"] == str(datetime.now(UTC).date())


def test_my_crew_today_no_assignment_404(client, tenant_id, user_id):
    """Returns 404 when the caller has no crew assignment today."""
    resp = client.get(
        "/vehicles/my-crew-today",
        headers=_headers(tenant_id, user_id),
    )
    assert resp.status_code == 404


def test_my_crew_today_missing_permission_403(client, tenant_id, user_id, crew_for_today):
    """Returns 403 when vehicles:read permission is missing."""
    resp = client.get(
        "/vehicles/my-crew-today",
        headers=_headers(tenant_id, user_id, perms="job:read"),
    )
    assert resp.status_code == 403


def test_my_crew_today_cross_tenant_isolation(client, tenant_id, user_id, v_repo, crew_repo):
    """A crew in another tenant is not visible."""
    other_tenant = uuid4()
    today = datetime.now(UTC).date()

    async def _setup():
        v = await v_repo.create(
            other_tenant, license_plate="OTH-001", nickname="Other Van",
            make="Ford", model="Transit", year=2022,
        )
        from office_hero.core.crew_role import CrewRole
        from office_hero.repositories.vehicle_crew_repository import CrewMemberInput

        await crew_repo.create(
            other_tenant,
            vehicle_id=v.id,
            work_date=today,
            shift_start=time(8, 0),
            shift_end=time(17, 0),
            notes=None,
            members=[CrewMemberInput(user_id=user_id, role_on_crew=CrewRole.LEAD)],
            created_by_user_id=user_id,
        )

    _run(_setup())
    resp = client.get(
        "/vehicles/my-crew-today",
        headers=_headers(tenant_id, user_id),
    )
    assert resp.status_code == 404
