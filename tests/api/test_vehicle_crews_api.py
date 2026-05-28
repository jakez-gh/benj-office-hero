"""HTTP-layer tests for the /vehicle-crews routes (RBAC + crew lifecycle)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, time
from typing import Any
from uuid import UUID, uuid4

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
# Helpers / fakes
# ---------------------------------------------------------------------------


class _FakeUser:
    def __init__(self, *, tenant_id, role="technician", active=True):
        self.id = uuid4()
        self.tenant_id = tenant_id
        self.role = role
        self.active = active


class _InMemoryUserRepo:
    def __init__(self):
        self._users: dict[UUID, _FakeUser] = {}

    def add(self, user: _FakeUser) -> _FakeUser:
        self._users[user.id] = user
        return user

    async def get_by_id(self, user_id: UUID, tenant_id: UUID) -> Any | None:
        u = self._users.get(user_id)
        if u is None or u.tenant_id != tenant_id:
            return None
        return u


class _VehicleCrewTestAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.tenant_id = request.headers.get("X-Test-Tenant-Id")
        request.state.user_id = request.headers.get("X-Test-User-Id")
        request.state.role = request.headers.get("X-Test-Role", "dispatcher")
        perms = request.headers.get("X-Test-Permissions", "vehicles:read")
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


def admin_headers(tenant_id, user_id) -> dict[str, str]:
    return {
        "X-Test-Tenant-Id": str(tenant_id),
        "X-Test-User-Id": str(user_id),
        "X-Test-Role": "tenant_admin",
        "X-Test-Permissions": "vehicles:read,vehicles:write",
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

WORK_DATE = date(2027, 9, 1)
WORK_DATE_ISO = WORK_DATE.isoformat()


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Give each test its own rate-limit bucket.

    All test requests share IP 127.0.0.1; without isolation, 60+ POSTs
    across the full suite exhaust the in-memory bucket and turn the
    duplicate-assignment test's expected 409 into a 429.

    We patch key_func on each registered Limit object so the bucket key
    is a fresh UUID per test, then restore it afterwards.
    """
    test_key = str(uuid4())
    saved: list[tuple] = []
    for limits in limiter._route_limits.values():
        for lim in limits:
            saved.append((lim, lim.key_func))
            lim.key_func = lambda *_a, **_k: test_key
    yield
    for lim, orig in saved:
        lim.key_func = orig


@pytest.fixture()
def tenant_a():
    return uuid4()


@pytest.fixture()
def tenant_b():
    return uuid4()


@pytest.fixture()
def user_repo():
    return _InMemoryUserRepo()


@pytest.fixture()
def audit():
    return InMemoryAuditService()


@pytest.fixture()
def v_repo():
    return InMemoryVehicleRepository()


@pytest.fixture()
def vc_repo():
    return InMemoryVehicleCrewRepository()


@pytest.fixture()
def vehicle_service(v_repo, vc_repo, audit):
    v_repo._crew_repo = vc_repo
    return VehicleService(repo=v_repo, audit=audit, crew_repo=vc_repo)


@pytest.fixture()
def crew_service(vc_repo, v_repo, user_repo, audit):
    return VehicleCrewService(
        crew_repo=vc_repo,
        vehicle_repo=v_repo,
        user_repo=user_repo,
        audit=audit,
    )


@pytest.fixture()
def app(vehicle_service, crew_service) -> FastAPI:
    a = create_app(vehicle_service=vehicle_service, vehicle_crew_service=crew_service)
    a.add_middleware(_VehicleCrewTestAuthMiddleware)
    return a


@pytest.fixture()
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def dispatcher_user_a(tenant_a, user_repo):
    return user_repo.add(_FakeUser(tenant_id=tenant_a, role="dispatcher"))


@pytest.fixture()
def tech_a(tenant_a, user_repo):
    return user_repo.add(_FakeUser(tenant_id=tenant_a, role="technician"))


@pytest.fixture()
def tech_b(tenant_a, user_repo):
    return user_repo.add(_FakeUser(tenant_id=tenant_a, role="technician"))


@pytest.fixture()
def vehicle_a(v_repo, tenant_a):
    import asyncio

    async def _create():
        return await v_repo.create(tenant_a, license_plate="CREW-API-001")

    return asyncio.get_event_loop().run_until_complete(_create())


def _crew_payload(vehicle_id, lead_user_id, work_date=WORK_DATE_ISO, **kwargs):
    return {
        "vehicle_id": str(vehicle_id),
        "work_date": work_date,
        "shift_start": "08:00:00",
        "shift_end": "17:00:00",
        "members": [{"user_id": str(lead_user_id), "role_on_crew": "lead"}],
        **kwargs,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_post_crew_dispatcher_succeeds(client, tenant_a, dispatcher_user_a, tech_a, vehicle_a):
    """Dispatcher can create a crew."""
    resp = client.post(
        "/vehicle-crews",
        json=_crew_payload(vehicle_a.id, tech_a.id),
        headers=dispatcher_headers(tenant_a, dispatcher_user_a.id),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["vehicle_id"] == str(vehicle_a.id)
    assert len(body["members"]) == 1


def test_post_crew_technician_403(client, tenant_a, tech_a, vehicle_a):
    """Technician cannot create a crew (role check)."""
    resp = client.post(
        "/vehicle-crews",
        json=_crew_payload(vehicle_a.id, tech_a.id),
        headers=technician_headers(tenant_a, tech_a.id),
    )
    assert resp.status_code == 403


def test_post_crew_duplicate_assignment_409(
    client, tenant_a, dispatcher_user_a, tech_a, tech_b, vehicle_a
):
    """Second crew for same (vehicle, date) returns 409."""
    client.post(
        "/vehicle-crews",
        json=_crew_payload(vehicle_a.id, tech_a.id),
        headers=dispatcher_headers(tenant_a, dispatcher_user_a.id),
    )
    resp = client.post(
        "/vehicle-crews",
        json=_crew_payload(vehicle_a.id, tech_b.id),
        headers=dispatcher_headers(tenant_a, dispatcher_user_a.id),
    )
    assert resp.status_code == 409


def test_post_crew_member_other_tenant_422_invalid_member(
    client, tenant_a, tenant_b, dispatcher_user_a, user_repo, vehicle_a
):
    """Member from another tenant returns 422 InvalidCrewMember."""
    other = user_repo.add(_FakeUser(tenant_id=tenant_b, role="technician"))
    resp = client.post(
        "/vehicle-crews",
        json=_crew_payload(vehicle_a.id, other.id),
        headers=dispatcher_headers(tenant_a, dispatcher_user_a.id),
    )
    assert resp.status_code == 422


def test_post_crew_no_lead_422(client, tenant_a, dispatcher_user_a, tech_a, vehicle_a):
    """A crew request with no LEAD member is rejected at schema layer (422)."""
    resp = client.post(
        "/vehicle-crews",
        json={
            "vehicle_id": str(vehicle_a.id),
            "work_date": WORK_DATE_ISO,
            "shift_start": "08:00:00",
            "shift_end": "17:00:00",
            "members": [{"user_id": str(tech_a.id), "role_on_crew": "helper"}],
        },
        headers=dispatcher_headers(tenant_a, dispatcher_user_a.id),
    )
    assert resp.status_code == 422


def test_get_crews_for_date_dispatcher_sees_all(
    client, tenant_a, dispatcher_user_a, tech_a, tech_b, v_repo, crew_service
):
    """Dispatcher listing /vehicle-crews?work_date=... sees all crews."""
    import asyncio

    async def _setup():
        v1 = await v_repo.create(tenant_a, license_plate="DS-V1")
        v2 = await v_repo.create(tenant_a, license_plate="DS-V2")
        await crew_service.create(
            tenant_a,
            dispatcher_user_a.id,
            vehicle_id=v1.id,
            work_date=WORK_DATE,
            shift_start=time(8, 0),
            shift_end=time(17, 0),
            notes=None,
            members=[CrewMemberInput(user_id=tech_a.id, role_on_crew=CrewRole.LEAD)],
        )
        await crew_service.create(
            tenant_a,
            dispatcher_user_a.id,
            vehicle_id=v2.id,
            work_date=WORK_DATE,
            shift_start=time(8, 0),
            shift_end=time(17, 0),
            notes=None,
            members=[CrewMemberInput(user_id=tech_b.id, role_on_crew=CrewRole.LEAD)],
        )

    asyncio.get_event_loop().run_until_complete(_setup())

    resp = client.get(
        f"/vehicle-crews?work_date={WORK_DATE_ISO}",
        headers=dispatcher_headers(tenant_a, dispatcher_user_a.id),
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


def test_get_crews_for_date_technician_sees_only_their_own(
    client, tenant_a, dispatcher_user_a, tech_a, tech_b, v_repo, crew_service
):
    """Technician listing sees only crews they are assigned to."""
    import asyncio

    async def _setup():
        v1 = await v_repo.create(tenant_a, license_plate="TC-V1")
        v2 = await v_repo.create(tenant_a, license_plate="TC-V2")
        c1 = await crew_service.create(
            tenant_a,
            dispatcher_user_a.id,
            vehicle_id=v1.id,
            work_date=WORK_DATE,
            shift_start=time(8, 0),
            shift_end=time(17, 0),
            notes=None,
            members=[CrewMemberInput(user_id=tech_a.id, role_on_crew=CrewRole.LEAD)],
        )
        c2 = await crew_service.create(
            tenant_a,
            dispatcher_user_a.id,
            vehicle_id=v2.id,
            work_date=WORK_DATE,
            shift_start=time(8, 0),
            shift_end=time(17, 0),
            notes=None,
            members=[CrewMemberInput(user_id=tech_b.id, role_on_crew=CrewRole.LEAD)],
        )
        return c1, c2

    c1, c2 = asyncio.get_event_loop().run_until_complete(_setup())

    resp = client.get(
        f"/vehicle-crews?work_date={WORK_DATE_ISO}",
        headers=technician_headers(tenant_a, tech_a.id),
    )
    assert resp.status_code == 200
    body = resp.json()
    ids = {item["id"] for item in body["items"]}
    assert str(c1.id) in ids
    assert str(c2.id) not in ids


def test_get_crew_conflicts_returns_double_booked_user(
    client, tenant_a, dispatcher_user_a, tech_a, tech_b, v_repo, crew_service
):
    """GET /vehicle-crews/conflicts returns users on multiple crews."""
    import asyncio

    async def _setup():
        v1 = await v_repo.create(tenant_a, license_plate="CF-V1")
        v2 = await v_repo.create(tenant_a, license_plate="CF-V2")
        await crew_service.create(
            tenant_a,
            dispatcher_user_a.id,
            vehicle_id=v1.id,
            work_date=WORK_DATE,
            shift_start=time(8, 0),
            shift_end=time(12, 0),
            notes=None,
            members=[CrewMemberInput(user_id=tech_a.id, role_on_crew=CrewRole.LEAD)],
        )
        await crew_service.create(
            tenant_a,
            dispatcher_user_a.id,
            vehicle_id=v2.id,
            work_date=WORK_DATE,
            shift_start=time(13, 0),
            shift_end=time(17, 0),
            notes=None,
            members=[
                CrewMemberInput(user_id=tech_b.id, role_on_crew=CrewRole.LEAD),
                CrewMemberInput(user_id=tech_a.id, role_on_crew=CrewRole.HELPER),
            ],
        )

    asyncio.get_event_loop().run_until_complete(_setup())

    resp = client.get(
        f"/vehicle-crews/conflicts?work_date={WORK_DATE_ISO}",
        headers=dispatcher_headers(tenant_a, dispatcher_user_a.id),
    )
    assert resp.status_code == 200
    conflict_user_ids = {item["user_id"] for item in resp.json()}
    assert str(tech_a.id) in conflict_user_ids


def test_replace_members_keeps_unique_user_invariant(
    client, tenant_a, dispatcher_user_a, tech_a, tech_b, vehicle_a, crew_service
):
    """PUT /vehicle-crews/{id}/members with duplicate user_id returns 422."""
    import asyncio

    async def _setup():
        return await crew_service.create(
            tenant_a,
            dispatcher_user_a.id,
            vehicle_id=vehicle_a.id,
            work_date=WORK_DATE,
            shift_start=time(8, 0),
            shift_end=time(17, 0),
            notes=None,
            members=[CrewMemberInput(user_id=tech_a.id, role_on_crew=CrewRole.LEAD)],
        )

    crew = asyncio.get_event_loop().run_until_complete(_setup())

    # Valid replace — one lead
    resp = client.put(
        f"/vehicle-crews/{crew.id}/members",
        json={
            "members": [
                {"user_id": str(tech_a.id), "role_on_crew": "lead"},
                {"user_id": str(tech_b.id), "role_on_crew": "helper"},
            ]
        },
        headers=dispatcher_headers(tenant_a, dispatcher_user_a.id),
    )
    assert resp.status_code == 200


def test_remove_lead_without_replacement_refused(
    client, tenant_a, dispatcher_user_a, tech_a, vehicle_a, crew_service
):
    """DELETE /vehicle-crews/{id}/members/{user_id} refuses to remove the only lead."""
    import asyncio

    async def _setup():
        return await crew_service.create(
            tenant_a,
            dispatcher_user_a.id,
            vehicle_id=vehicle_a.id,
            work_date=WORK_DATE,
            shift_start=time(8, 0),
            shift_end=time(17, 0),
            notes=None,
            members=[CrewMemberInput(user_id=tech_a.id, role_on_crew=CrewRole.LEAD)],
        )

    crew = asyncio.get_event_loop().run_until_complete(_setup())

    resp = client.delete(
        f"/vehicle-crews/{crew.id}/members/{tech_a.id}",
        headers=dispatcher_headers(tenant_a, dispatcher_user_a.id),
    )
    assert resp.status_code == 409
