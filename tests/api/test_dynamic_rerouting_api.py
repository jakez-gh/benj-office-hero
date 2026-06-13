"""HTTP-layer tests for day-of re-routing (Slice 16).

POST /routes/{id}/reassign and POST /jobs/{id}/emergency-dispatch.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from office_hero.adapters.routing.stub import StubRoutingAdapter
from office_hero.api.app import create_app
from office_hero.api.state import (
    set_dispatch_service,
    set_dynamic_dispatch_service,
    set_route_repository,
    set_route_stop_repository,
)
from office_hero.core.crew_role import CrewRole
from office_hero.repositories.job_repository import InMemoryJobRepository
from office_hero.repositories.mocks import InMemoryAuditService
from office_hero.repositories.route_repository import InMemoryRouteRepository, RouteCreateRow
from office_hero.repositories.route_stop_repository import InMemoryRouteStopRepository, StopRow
from office_hero.repositories.vehicle_crew_repository import (
    CrewMemberInput,
    InMemoryVehicleCrewRepository,
)
from office_hero.repositories.vehicle_repository import InMemoryVehicleRepository
from office_hero.services.dispatch_service import DispatchService
from office_hero.services.dynamic_dispatch_service import DynamicDispatchService
from office_hero.services.schedule_suggestion_service import ScheduleSuggestionService

WORK_DATE = date(2026, 6, 15)


class _AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.tenant_id = request.headers.get("X-Test-Tenant-Id")
        request.state.user_id = request.headers.get("X-Test-User-Id")
        request.state.role = request.headers.get("X-Test-Role", "dispatcher")
        perms = request.headers.get("X-Test-Permissions", "")
        request.state.permissions = [p.strip() for p in perms.split(",") if p.strip()]
        return await call_next(request)


def _headers(tenant_id, user_id, *, perms="route:write,route:read,jobs:dispatch,vehicle:read"):
    return {
        "X-Test-Tenant-Id": str(tenant_id),
        "X-Test-User-Id": str(user_id),
        "X-Test-Role": "dispatcher",
        "X-Test-Permissions": perms,
    }


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture()
def setup():
    tenant_id = uuid4()
    user_id = uuid4()
    job_repo = InMemoryJobRepository()
    vehicle_repo = InMemoryVehicleRepository()
    vc_repo = InMemoryVehicleCrewRepository()
    route_repo = InMemoryRouteRepository()
    stop_repo = InMemoryRouteStopRepository()
    audit = InMemoryAuditService()
    schedule_svc = ScheduleSuggestionService(
        job_repo=job_repo,
        vehicle_repo=vehicle_repo,
        routing_adapter=StubRoutingAdapter(),
        vehicle_location_repo=None,
    )
    dispatch_svc = DispatchService(
        route_repo=route_repo,
        stop_repo=stop_repo,
        job_repo=job_repo,
        vehicle_repo=vehicle_repo,
        vehicle_crew_repo=vc_repo,
        schedule_service=schedule_svc,
        audit=audit,
    )
    dynamic_svc = DynamicDispatchService(
        route_repo=route_repo,
        stop_repo=stop_repo,
        job_repo=job_repo,
        vehicle_repo=vehicle_repo,
        vehicle_crew_repo=vc_repo,
        schedule_service=schedule_svc,
        audit=audit,
    )

    set_route_repository(route_repo)
    set_route_stop_repository(stop_repo)
    set_dispatch_service(dispatch_svc)
    set_dynamic_dispatch_service(dynamic_svc)

    from office_hero.api.limiter import limiter

    saved = dict(limiter._route_limits)
    limiter._route_limits.clear()
    app = create_app(dispatch_service=dispatch_svc, dynamic_dispatch_service=dynamic_svc)
    app.add_middleware(_AuthMiddleware)

    test_key = str(uuid4())
    saved_keys = []
    for limits in limiter._route_limits.values():
        for lim in limits:
            saved_keys.append((lim, lim.key_func))
            lim.key_func = lambda *_a, **_k: test_key

    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client,
            tenant_id=tenant_id,
            user_id=user_id,
            job_repo=job_repo,
            vehicle_repo=vehicle_repo,
            vc_repo=vc_repo,
            route_repo=route_repo,
            stop_repo=stop_repo,
        )

    for lim, orig in saved_keys:
        lim.key_func = orig
    limiter._route_limits.clear()
    limiter._route_limits.update(saved)


async def _vehicle_with_crew(s, plate):
    v = await s.vehicle_repo.create(
        s.tenant_id, license_plate=plate, nickname=plate, make="Ford", model="Transit", year=2022
    )
    await s.vc_repo.create(
        s.tenant_id,
        vehicle_id=v.id,
        work_date=WORK_DATE,
        shift_start=time(8, 0),
        shift_end=time(17, 0),
        notes=None,
        created_by_user_id=s.user_id,
        members=[CrewMemberInput(user_id=s.user_id, role_on_crew=CrewRole.LEAD)],
    )
    return v


async def _job(s, title, *, geocoded=False):
    loc_id = uuid4()
    job = await s.job_repo.create(
        s.tenant_id,
        customer_id=uuid4(),
        location_id=loc_id,
        industry="generic",
        title=title,
        created_by_user_id=s.user_id,
    )
    if geocoded:
        orig = s.job_repo.get_by_id

        async def patched(jid, tid, _orig=orig):
            j = await _orig(jid, tid)
            if j is not None and j.location_id == loc_id:
                j.location = SimpleNamespace(lat=Decimal("34.05"), lng=Decimal("-118.24"))
            return j

        s.job_repo.get_by_id = patched
    return job


async def _committed_route(s, vehicle, jobs):
    route = await s.route_repo.create(
        s.tenant_id,
        row=RouteCreateRow(
            vehicle_id=vehicle.id,
            vehicle_crew_id=uuid4(),
            work_date=WORK_DATE,
            committed_by_user_id=s.user_id,
            option_kind_applied="manual",
            notes=None,
            total_distance_m=1000 * len(jobs),
            total_duration_s=600 * len(jobs),
        ),
    )
    stops = await s.stop_repo.bulk_insert(
        s.tenant_id,
        route.id,
        [
            StopRow(
                job_id=j.id,
                sequence_index=i,
                planned_distance_from_prev_m=1000,
                planned_duration_from_prev_s=600,
            )
            for i, j in enumerate(jobs)
        ],
    )
    route.stops = stops
    return route


# ---------------------------------------------------------------------------
# POST /routes/{id}/reassign
# ---------------------------------------------------------------------------


def test_reassign_requires_route_write(setup):
    s = setup
    resp = s.client.post(
        f"/routes/{uuid4()}/reassign",
        json={"target_vehicle_id": str(uuid4())},
        headers=_headers(s.tenant_id, s.user_id, perms="route:read"),
    )
    assert resp.status_code == 403


def test_reassign_happy_path(setup):
    s = setup
    va = _run(_vehicle_with_crew(s, "A"))
    vb = _run(_vehicle_with_crew(s, "B"))
    j1 = _run(_job(s, "J1"))
    j2 = _run(_job(s, "J2"))
    route = _run(_committed_route(s, va, [j1, j2]))

    resp = s.client.post(
        f"/routes/{route.id}/reassign",
        json={"target_vehicle_id": str(vb.id)},
        headers=_headers(s.tenant_id, s.user_id),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["moved_count"] == 2
    assert body["source_route"]["status"] == "cancelled"
    assert [st["job_id"] for st in body["target_route"]["stops"]] == [str(j1.id), str(j2.id)]


def test_reassign_no_crew_target_409(setup):
    s = setup
    va = _run(_vehicle_with_crew(s, "A"))
    vb = _run(
        s.vehicle_repo.create(
            s.tenant_id, license_plate="NOCREW", nickname="NoCrew", make="F", model="T", year=2022
        )
    )
    j1 = _run(_job(s, "J1"))
    route = _run(_committed_route(s, va, [j1]))

    resp = s.client.post(
        f"/routes/{route.id}/reassign",
        json={"target_vehicle_id": str(vb.id)},
        headers=_headers(s.tenant_id, s.user_id),
    )
    assert resp.status_code == 409


def test_reassign_unknown_route_404(setup):
    s = setup
    resp = s.client.post(
        f"/routes/{uuid4()}/reassign",
        json={"target_vehicle_id": str(uuid4())},
        headers=_headers(s.tenant_id, s.user_id),
    )
    assert resp.status_code == 404


def test_reassign_cross_tenant_route_404(setup):
    s = setup
    va = _run(_vehicle_with_crew(s, "A"))
    vb = _run(_vehicle_with_crew(s, "B"))
    j1 = _run(_job(s, "J1"))
    route = _run(_committed_route(s, va, [j1]))

    other_tenant = uuid4()
    resp = s.client.post(
        f"/routes/{route.id}/reassign",
        json={"target_vehicle_id": str(vb.id)},
        headers=_headers(other_tenant, s.user_id),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /jobs/{id}/emergency-dispatch
# ---------------------------------------------------------------------------


def _window_body(target=None):
    start = datetime.combine(WORK_DATE, time(9, 0), tzinfo=UTC)
    end = start + timedelta(hours=8)
    body = {"window_start": start.isoformat(), "window_end": end.isoformat()}
    if target is not None:
        body["target_vehicle_id"] = str(target)
    return body


def test_emergency_requires_permissions(setup):
    s = setup
    resp = s.client.post(
        f"/jobs/{uuid4()}/emergency-dispatch",
        json=_window_body(uuid4()),
        headers=_headers(s.tenant_id, s.user_id, perms="route:read"),
    )
    assert resp.status_code == 403


def test_emergency_explicit_target_front_inserts(setup):
    s = setup
    va = _run(_vehicle_with_crew(s, "A"))
    routine = _run(_job(s, "routine"))
    _run(_committed_route(s, va, [routine]))
    emergency = _run(_job(s, "EMERGENCY"))

    resp = s.client.post(
        f"/jobs/{emergency.id}/emergency-dispatch",
        json=_window_body(va.id),
        headers=_headers(s.tenant_id, s.user_id),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert [st["job_id"] for st in body["stops"]] == [str(emergency.id), str(routine.id)]
    refreshed = _run(s.job_repo.get_by_id(emergency.id, s.tenant_id))
    assert refreshed.status == "scheduled"


def test_emergency_auto_pick_creates_route(setup):
    s = setup
    _run(_vehicle_with_crew(s, "A"))  # active vehicle for the schedule service to pick
    emergency = _run(_job(s, "EMERGENCY", geocoded=True))

    resp = s.client.post(
        f"/jobs/{emergency.id}/emergency-dispatch",
        json=_window_body(),  # no target → schedule service picks
        headers=_headers(s.tenant_id, s.user_id),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["option_kind_applied"] == "emergency"


def test_emergency_no_vehicle_available_409(setup):
    s = setup
    emergency = _run(_job(s, "EMERGENCY", geocoded=True))  # no active vehicles
    resp = s.client.post(
        f"/jobs/{emergency.id}/emergency-dispatch",
        json=_window_body(),
        headers=_headers(s.tenant_id, s.user_id),
    )
    assert resp.status_code == 409


def test_emergency_invalid_window_422(setup):
    s = setup
    start = datetime.combine(WORK_DATE, time(9, 0), tzinfo=UTC)
    resp = s.client.post(
        f"/jobs/{uuid4()}/emergency-dispatch",
        json={"window_start": start.isoformat(), "window_end": start.isoformat()},
        headers=_headers(s.tenant_id, s.user_id),
    )
    assert resp.status_code == 422
