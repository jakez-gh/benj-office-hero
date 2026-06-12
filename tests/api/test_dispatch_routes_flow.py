"""HTTP-layer tests for the dispatch → Route flow (suggested + manual override).

Covers the gap the original Slice-14 tests left open:
* POST /jobs/{id}/dispatch (the admin "pick a suggested slot" path) must
  create/append persistent Route + RouteStop records, not just flip job state.
* POST /routes manual mode (custom vehicle + sequence) — the "fourth option".
* POST /routes/{id}/resequence — reordering a committed route.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, time, timedelta
from uuid import uuid4

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

from office_hero.api.app import create_app
from office_hero.api.state import (
    set_dispatch_service,
    set_route_repository,
    set_route_stop_repository,
)
from office_hero.core.crew_role import CrewRole
from office_hero.repositories.job_repository import InMemoryJobRepository
from office_hero.repositories.mocks import InMemoryAuditService
from office_hero.repositories.route_repository import InMemoryRouteRepository
from office_hero.repositories.route_stop_repository import InMemoryRouteStopRepository
from office_hero.repositories.vehicle_crew_repository import (
    CrewMemberInput,
    InMemoryVehicleCrewRepository,
)
from office_hero.repositories.vehicle_repository import InMemoryVehicleRepository
from office_hero.services.dispatch_service import DispatchService
from office_hero.services.job_dispatch_service import JobDispatchService


class _FlowAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.tenant_id = request.headers.get("X-Test-Tenant-Id")
        request.state.user_id = request.headers.get("X-Test-User-Id")
        request.state.role = request.headers.get("X-Test-Role", "dispatcher")
        perms = request.headers.get("X-Test-Permissions", "")
        request.state.permissions = [p.strip() for p in perms.split(",") if p.strip()]
        return await call_next(request)


def _auth_headers(tenant_id, user_id):
    return {
        "X-Test-Tenant-Id": str(tenant_id),
        "X-Test-User-Id": str(user_id),
        "X-Test-Role": "dispatcher",
        "X-Test-Permissions": "route:write,route:read,job:write,vehicle:read",
    }


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _isolate_rate_limit_key() -> list[tuple]:
    """Point every registered rate limit at a fresh key (see golden path test)."""
    from office_hero.api.limiter import limiter

    test_key = str(uuid4())
    saved: list[tuple] = []
    for limits in limiter._route_limits.values():
        for lim in limits:
            saved.append((lim, lim.key_func))
            lim.key_func = lambda *_a, **_k: test_key
    return saved


@pytest.fixture()
def setup():
    """Full app with shared job/vehicle/route repos and both dispatch services."""
    tenant_id = uuid4()
    user_id = uuid4()

    job_repo = InMemoryJobRepository()
    vehicle_repo = InMemoryVehicleRepository()
    vc_repo = InMemoryVehicleCrewRepository()
    route_repo = InMemoryRouteRepository()
    stop_repo = InMemoryRouteStopRepository()
    audit = InMemoryAuditService()

    job_dispatch_svc = JobDispatchService(
        job_repo=job_repo,
        vehicle_repo=vehicle_repo,
        route_repo=route_repo,
        stop_repo=stop_repo,
        crew_repo=vc_repo,
    )
    dispatch_svc = DispatchService(
        route_repo=route_repo,
        stop_repo=stop_repo,
        job_repo=job_repo,
        vehicle_repo=vehicle_repo,
        vehicle_crew_repo=vc_repo,
        schedule_service=None,  # manual mode + resequence don't consult it
        audit=audit,
    )

    set_route_repository(route_repo)
    set_route_stop_repository(stop_repo)
    set_dispatch_service(dispatch_svc)

    from office_hero.api.limiter import limiter

    saved_route_limits = dict(limiter._route_limits)
    limiter._route_limits.clear()
    app = create_app(
        job_dispatch_service=job_dispatch_svc,
        dispatch_service=dispatch_svc,
    )
    app.add_middleware(_FlowAuthMiddleware)

    saved_key_funcs = _isolate_rate_limit_key()

    with TestClient(app) as client:
        yield {
            "client": client,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "job_repo": job_repo,
            "vehicle_repo": vehicle_repo,
            "vc_repo": vc_repo,
            "route_repo": route_repo,
            "stop_repo": stop_repo,
        }

    for lim, orig in saved_key_funcs:
        lim.key_func = orig
    limiter._route_limits.clear()
    limiter._route_limits.update(saved_route_limits)


async def _seed_vehicle_with_crew(setup_data, *, work_date=None):
    tenant_id = setup_data["tenant_id"]
    user_id = setup_data["user_id"]
    vehicle = await setup_data["vehicle_repo"].create(
        tenant_id,
        license_plate="ABC-123",
        nickname="Van #1",
        make="Ford",
        model="Transit",
        year=2022,
    )
    await setup_data["vc_repo"].create(
        tenant_id,
        vehicle_id=vehicle.id,
        work_date=work_date or date.today(),
        shift_start=time(8, 0),
        shift_end=time(17, 0),
        notes=None,
        created_by_user_id=user_id,
        members=[CrewMemberInput(user_id=user_id, role_on_crew=CrewRole.LEAD)],
    )
    return vehicle


async def _seed_job(setup_data, *, title="Fix leaking pipe"):
    return await setup_data["job_repo"].create(
        setup_data["tenant_id"],
        customer_id=uuid4(),
        location_id=uuid4(),
        industry="plumbing",
        title=title,
        created_by_user_id=setup_data["user_id"],
    )


def _slot(hour: int) -> str:
    return (
        datetime.combine(date.today(), time(hour, 0), tzinfo=UTC) + timedelta(days=0)
    ).isoformat()


# ---------------------------------------------------------------------------
# POST /jobs/{id}/dispatch — suggested-slot path now creates Routes
# ---------------------------------------------------------------------------


def test_dispatch_creates_route_and_stop(setup):
    client = setup["client"]
    headers = _auth_headers(setup["tenant_id"], setup["user_id"])
    vehicle = _run(_seed_vehicle_with_crew(setup))
    job = _run(_seed_job(setup))

    resp = client.post(
        f"/jobs/{job.id}/dispatch",
        json={
            "vehicle_id": str(vehicle.id),
            "scheduled_for": _slot(9),
            "travel_seconds": 900,
            "distance_meters": 12000,
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "scheduled"
    assert body["route_id"] is not None

    route = client.get(f"/routes/{body['route_id']}", headers=headers).json()
    assert route["status"] == "committed"
    assert route["option_kind_applied"] == "suggested"
    assert route["total_duration_s"] == 900
    assert len(route["stops"]) == 1
    assert route["stops"][0]["job_id"] == str(job.id)
    assert route["stops"][0]["sequence_index"] == 0


def test_second_dispatch_same_vehicle_appends_stop(setup):
    client = setup["client"]
    headers = _auth_headers(setup["tenant_id"], setup["user_id"])
    vehicle = _run(_seed_vehicle_with_crew(setup))
    job1 = _run(_seed_job(setup, title="Morning job"))
    job2 = _run(_seed_job(setup, title="Afternoon job"))

    first = client.post(
        f"/jobs/{job1.id}/dispatch",
        json={"vehicle_id": str(vehicle.id), "scheduled_for": _slot(9)},
        headers=headers,
    )
    assert first.status_code == 200, first.text
    second = client.post(
        f"/jobs/{job2.id}/dispatch",
        json={"vehicle_id": str(vehicle.id), "scheduled_for": _slot(13)},
        headers=headers,
    )
    assert second.status_code == 200, second.text
    assert second.json()["route_id"] == first.json()["route_id"]

    route = client.get(f"/routes/{first.json()['route_id']}", headers=headers).json()
    assert [s["job_id"] for s in route["stops"]] == [str(job1.id), str(job2.id)]
    assert [s["sequence_index"] for s in route["stops"]] == [0, 1]


def test_dispatch_without_crew_409_and_job_untouched(setup):
    client = setup["client"]
    headers = _auth_headers(setup["tenant_id"], setup["user_id"])
    # Vehicle WITHOUT a crew for today.
    vehicle = _run(
        setup["vehicle_repo"].create(
            setup["tenant_id"],
            license_plate="NOCREW-1",
            nickname="Crewless",
            make="Ford",
            model="Transit",
            year=2022,
        )
    )
    job = _run(_seed_job(setup))

    resp = client.post(
        f"/jobs/{job.id}/dispatch",
        json={"vehicle_id": str(vehicle.id), "scheduled_for": _slot(9)},
        headers=headers,
    )
    assert resp.status_code == 409
    assert "crew" in resp.json()["detail"].lower()

    refreshed = _run(setup["job_repo"].get_by_id(job.id, setup["tenant_id"]))
    assert refreshed.status == "pending"
    assert refreshed.assigned_vehicle_id is None


# ---------------------------------------------------------------------------
# POST /routes — manual mode (the "fourth custom option")
# ---------------------------------------------------------------------------


def test_manual_commit_creates_route_with_custom_sequence(setup):
    client = setup["client"]
    headers = _auth_headers(setup["tenant_id"], setup["user_id"])
    vehicle = _run(_seed_vehicle_with_crew(setup))
    job1 = _run(_seed_job(setup, title="Stop A"))
    job2 = _run(_seed_job(setup, title="Stop B"))

    resp = client.post(
        f"/routes?job_id={job1.id}",
        json={
            "date": date.today().isoformat(),
            "manual_vehicle_id": str(vehicle.id),
            "manual_sequence": [str(job2.id), str(job1.id)],
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    route = resp.json()
    assert route["option_kind_applied"] == "manual"
    assert [s["job_id"] for s in route["stops"]] == [str(job2.id), str(job1.id)]


def test_manual_commit_with_unknown_job_422(setup):
    client = setup["client"]
    headers = _auth_headers(setup["tenant_id"], setup["user_id"])
    vehicle = _run(_seed_vehicle_with_crew(setup))
    job = _run(_seed_job(setup))

    resp = client.post(
        f"/routes?job_id={job.id}",
        json={
            "date": date.today().isoformat(),
            "manual_vehicle_id": str(vehicle.id),
            "manual_sequence": [str(job.id), str(uuid4())],
        },
        headers=headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /routes/{id}/resequence — reorder a committed route
# ---------------------------------------------------------------------------


def _commit_two_stop_route(setup) -> tuple[str, str, str]:
    """Dispatch two jobs onto one vehicle; return (route_id, job1_id, job2_id)."""
    client = setup["client"]
    headers = _auth_headers(setup["tenant_id"], setup["user_id"])
    vehicle = _run(_seed_vehicle_with_crew(setup))
    job1 = _run(_seed_job(setup, title="First"))
    job2 = _run(_seed_job(setup, title="Second"))
    first = client.post(
        f"/jobs/{job1.id}/dispatch",
        json={"vehicle_id": str(vehicle.id), "scheduled_for": _slot(9)},
        headers=headers,
    )
    client.post(
        f"/jobs/{job2.id}/dispatch",
        json={"vehicle_id": str(vehicle.id), "scheduled_for": _slot(13)},
        headers=headers,
    )
    return first.json()["route_id"], str(job1.id), str(job2.id)


def test_resequence_reorders_stops(setup):
    client = setup["client"]
    headers = _auth_headers(setup["tenant_id"], setup["user_id"])
    route_id, job1_id, job2_id = _commit_two_stop_route(setup)

    resp = client.post(
        f"/routes/{route_id}/resequence",
        json={"job_ids": [job2_id, job1_id]},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    route = resp.json()
    assert [s["job_id"] for s in route["stops"]] == [job2_id, job1_id]
    assert [s["sequence_index"] for s in route["stops"]] == [0, 1]


def test_resequence_rejects_non_permutation_422(setup):
    client = setup["client"]
    headers = _auth_headers(setup["tenant_id"], setup["user_id"])
    route_id, job1_id, _job2_id = _commit_two_stop_route(setup)

    resp = client.post(
        f"/routes/{route_id}/resequence",
        json={"job_ids": [job1_id, str(uuid4())]},
        headers=headers,
    )
    assert resp.status_code == 422


def test_resequence_rejects_in_progress_route_422(setup):
    client = setup["client"]
    headers = _auth_headers(setup["tenant_id"], setup["user_id"])
    route_id, job1_id, job2_id = _commit_two_stop_route(setup)

    started = client.post(f"/routes/{route_id}/start", headers=headers)
    assert started.status_code == 200

    resp = client.post(
        f"/routes/{route_id}/resequence",
        json={"job_ids": [job2_id, job1_id]},
        headers=headers,
    )
    assert resp.status_code == 422


def test_resequence_route_not_found_404(setup):
    client = setup["client"]
    headers = _auth_headers(setup["tenant_id"], setup["user_id"])
    resp = client.post(
        f"/routes/{uuid4()}/resequence",
        json={"job_ids": [str(uuid4())]},
        headers=headers,
    )
    assert resp.status_code == 404
