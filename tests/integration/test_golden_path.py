"""Golden path smoke test for Office Hero MVP dispatch flow."""

import asyncio
from datetime import date, datetime, time, UTC
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from office_hero.api.app import create_app
from office_hero.repositories.job_repository import InMemoryJobRepository
from office_hero.repositories.vehicle_repository import InMemoryVehicleRepository
from office_hero.repositories.route_repository import InMemoryRouteRepository
from office_hero.repositories.route_stop_repository import InMemoryRouteStopRepository
from office_hero.repositories.customer_repository import InMemoryCustomerRepository
from office_hero.repositories.location_repository import InMemoryLocationRepository
from office_hero.repositories.vehicle_crew_repository import (
    CrewMemberInput,
    InMemoryVehicleCrewRepository,
)
from office_hero.core.crew_role import CrewRole
from office_hero.repositories.mocks import InMemoryAuditService
from office_hero.services.dispatch_service import DispatchService
from office_hero.services.job_service import JobService
from office_hero.services.vehicle_service import VehicleService
from office_hero.services.vehicle_crew_service import VehicleCrewService
from office_hero.services.schedule_suggestion_service import ScheduleSuggestionService
from office_hero.adapters.routing.stub import StubRoutingAdapter
from office_hero.api.state import (
    set_route_repository, set_route_stop_repository, set_dispatch_service,
    set_job_service, set_vehicle_service, set_vehicle_crew_service,
    set_schedule_suggestion_service,
)
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class _GoldenPathAuthMiddleware(BaseHTTPMiddleware):
    """Test auth middleware - sets request.state from headers."""
    async def dispatch(self, request: Request, call_next):
        request.state.tenant_id = request.headers.get("X-Test-Tenant-Id")
        request.state.user_id = request.headers.get("X-Test-User-Id")
        request.state.role = request.headers.get("X-Test-Role", "dispatcher")
        perms_raw = request.headers.get("X-Test-Permissions", "route:write,route:read")
        request.state.permissions = [p.strip() for p in perms_raw.split(",") if p.strip()]
        return await call_next(request)


def _auth_headers(tenant_id, user_id):
    return {
        "X-Test-Tenant-Id": str(tenant_id),
        "X-Test-User-Id": str(user_id),
        "X-Test-Role": "dispatcher",
        "X-Test-Permissions": "route:write,route:read,jobs:write,jobs:read",
    }


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture()
def setup():
    """Set up all repositories and services."""
    tenant_id = uuid4()
    user_id = uuid4()
    customer_id = uuid4()
    location_id = uuid4()
    vehicle_id = None
    
    # Repositories
    job_repo = InMemoryJobRepository()
    vehicle_repo = InMemoryVehicleRepository()
    vc_repo = InMemoryVehicleCrewRepository()
    route_repo = InMemoryRouteRepository()
    stop_repo = InMemoryRouteStopRepository()
    cust_repo = InMemoryCustomerRepository()
    loc_repo = InMemoryLocationRepository()
    audit = InMemoryAuditService()
    
    # Services
    routing_adapter = StubRoutingAdapter()
    schedule_svc = ScheduleSuggestionService(
        job_repo=job_repo,
        vehicle_repo=vehicle_repo,
        routing_adapter=routing_adapter,
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
    # Create a simple mock template registry
    class MockTemplateRegistry:
        @staticmethod
        def get_template(industry):
            from office_hero.services.custom_field_templates.generic import GenericTemplate
            return GenericTemplate()

    job_svc = JobService(
        repo=job_repo,
        customer_repo=cust_repo,
        location_repo=loc_repo,
        audit=audit,
        template_registry=MockTemplateRegistry(),
    )
    vehicle_svc = VehicleService(repo=vehicle_repo, audit=audit, crew_repo=vc_repo)
    vc_svc = VehicleCrewService(
        crew_repo=vc_repo,
        vehicle_repo=vehicle_repo,
        user_repo=None,
        audit=audit,
    )
    
    # Wire providers
    set_job_service(job_svc)
    set_vehicle_service(vehicle_svc)
    set_vehicle_crew_service(vc_svc)
    set_schedule_suggestion_service(schedule_svc)
    set_route_repository(route_repo)
    set_route_stop_repository(stop_repo)
    set_dispatch_service(dispatch_svc)
    
    # Create app
    app = create_app(
        job_service=job_svc,
        vehicle_service=vehicle_svc,
        vehicle_crew_service=vc_svc,
        schedule_suggestion_service=schedule_svc,
        dispatch_service=dispatch_svc,
    )
    app.add_middleware(_GoldenPathAuthMiddleware)
    
    with TestClient(app) as client:
        return {
            "client": client,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "customer_id": customer_id,
            "location_id": location_id,
            "job_repo": job_repo,
            "vehicle_repo": vehicle_repo,
            "route_repo": route_repo,
            "stop_repo": stop_repo,
            "cust_repo": cust_repo,
            "loc_repo": loc_repo,
            "vc_repo": vc_repo,
        }


def test_golden_path_dispatch_flow(setup):
    """Execute the complete golden path: job â†’ dispatch â†’ route â†’ stops."""
    client = setup["client"]
    tenant_id = setup["tenant_id"]
    user_id = setup["user_id"]
    customer_id = setup["customer_id"]
    location_id = setup["location_id"]
    job_repo = setup["job_repo"]
    vehicle_repo = setup["vehicle_repo"]
    cust_repo = setup["cust_repo"]
    loc_repo = setup["loc_repo"]

    auth_headers = _auth_headers(tenant_id, user_id)

    print("\n=== Step 0: Seed Customer and Location ===")
    async def seed_data():
        cust = await cust_repo.create(tenant_id, name="Test Customer", email="test@example.com")
        loc = await loc_repo.create(
            tenant_id,
            customer_id=cust.id,
            street="123 Main St",
            city="Anytown",
            state="CA",
            postal_code="12345",
        )
        # Geocode the location with test coordinates
        await loc_repo.set_coordinates(
            loc.id,
            tenant_id,
            lat=34.0522,
            lng=-118.2437,
            source="test",
        )
        return cust.id, loc.id
    cid, lid = _run(seed_data())
    customer_id = cid
    location_id = lid
    print(f"âœ… PASS: Seeded customer {customer_id} and location {location_id}")

    print("\n=== Step 1: Health Check ===")
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    print("âœ… PASS: Health check")

    print("\n=== Step 2: Create Vehicle (with crew for today) ===")
    async def create_vehicle():
        vehicle = await vehicle_repo.create(
            tenant_id,
            license_plate="ABC-123",
            nickname="Van #1",
            make="Ford",
            model="Transit",
            year=2022,
        )
        # Dispatch requires a crew assigned to the vehicle for the work date.
        await setup["vc_repo"].create(
            tenant_id,
            vehicle_id=vehicle.id,
            work_date=date.today(),
            shift_start=time(8, 0),
            shift_end=time(17, 0),
            notes=None,
            created_by_user_id=user_id,
            members=[CrewMemberInput(user_id=user_id, role_on_crew=CrewRole.LEAD)],
        )
        return vehicle
    vehicle = _run(create_vehicle())
    vehicle_id = vehicle.id
    print(f"âœ… PASS: Vehicle created {vehicle_id}")

    # The in-memory job repository does not hydrate the ``job.location``
    # relationship, but the scheduling engine reads job.location.lat/lng.
    # Wrap get_by_id to attach the seeded (geocoded) location.
    original_get_by_id = job_repo.get_by_id

    async def get_by_id_with_location(jid, tid):
        job = await original_get_by_id(jid, tid)
        if job is not None:
            job.location = await loc_repo.get_by_id(job.location_id, tid)
        return job

    job_repo.get_by_id = get_by_id_with_location
    
    print("\n=== Step 3: Create Job ===")
    resp = client.post(
        "/jobs",
        json={
            "customer_id": str(customer_id),
            "location_id": str(location_id),
            "title": "Fix leaking pipe",
            "service_type": "Drain cleaning",
            "priority": 50,
            "estimated_duration_min": 60,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, f"Job creation failed: {resp.json()}"
    job_data = resp.json()
    job_id = job_data["id"]
    assert job_data["status"] == "pending"
    print(f"âœ… PASS: Job created {job_id} with status={job_data['status']}")
    
    print("\n=== Step 4: Dispatch Job to Create Route ===")
    test_date = date.today().isoformat()
    resp = client.post(
        f"/routes?job_id={job_id}",
        json={"date": test_date, "option_kind": "nearest"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, f"Route creation failed: {resp.json()}"
    route_data = resp.json()
    route_id = route_data["id"]
    assert route_data["status"] == "committed"
    assert len(route_data["stops"]) > 0
    stop_id = route_data["stops"][0]["id"]
    print(f"âœ… PASS: Route created {route_id} with status={route_data['status']}")
    print(f"         First stop: {stop_id}")
    
    print("\n=== Step 5: List Routes ===")
    resp = client.get(
        f"/routes?date={test_date}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    list_data = resp.json()
    assert list_data["total"] > 0
    assert any(r["id"] == route_id for r in list_data["items"])
    print(f"âœ… PASS: Routes listed, found {list_data['total']} routes")
    
    print("\n=== Step 6: Get Route by ID ===")
    resp = client.get(
        f"/routes/{route_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    route_data = resp.json()
    assert route_data["id"] == route_id
    assert route_data["status"] == "committed"
    print(f"âœ… PASS: Route retrieved: {route_id}")
    
    print("\n=== Step 7: Start Route ===")
    resp = client.post(
        f"/routes/{route_id}/start",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    route_data = resp.json()
    assert route_data["status"] == "in_progress"
    print(f"âœ… PASS: Route started, status={route_data['status']}")
    
    print("\n=== Step 8: Mark Stop Arrived ===")
    resp = client.post(
        f"/routes/{route_id}/stops/{stop_id}/arrived",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    route_data = resp.json()
    found_stop = next((s for s in route_data["stops"] if s["id"] == stop_id), None)
    assert found_stop is not None
    assert found_stop["status"] == "arrived"
    print(f"âœ… PASS: Stop marked arrived")
    
    print("\n=== Step 9: Mark Stop Complete ===")
    resp = client.post(
        f"/routes/{route_id}/stops/{stop_id}/complete",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    route_data = resp.json()
    found_stop = next((s for s in route_data["stops"] if s["id"] == stop_id), None)
    assert found_stop is not None
    assert found_stop["status"] == "complete"
    
    # Check if route auto-completes (depends on whether there are other stops)
    if len(route_data["stops"]) == 1:
        assert route_data["status"] == "complete", "Route should auto-complete when all stops terminal"
    
    print(f"âœ… PASS: Stop marked complete")
    print(f"         Route status: {route_data['status']}")
    
    print("\n" + "="*60)
    print("ðŸŽ‰ GOLDEN PATH COMPLETE - ALL 9 STEPS PASSED")
    print("="*60)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
