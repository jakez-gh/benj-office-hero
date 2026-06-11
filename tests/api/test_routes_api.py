"""API contract tests for Slice 14 route management endpoints."""

from datetime import date
from uuid import uuid4

import pytest
from fastapi import Request
from httpx import ASGITransport, AsyncClient
from starlette.middleware.base import BaseHTTPMiddleware

from office_hero.adapters.routing.stub import StubRoutingAdapter
from office_hero.api.app import create_app
from office_hero.api.state import (
    set_dispatch_service,
    set_job_service,
    set_route_repository,
    set_route_stop_repository,
    set_schedule_suggestion_service,
    set_vehicle_crew_service,
    set_vehicle_service,
)
from office_hero.repositories.customer_repository import InMemoryCustomerRepository
from office_hero.repositories.job_repository import InMemoryJobRepository
from office_hero.repositories.location_repository import InMemoryLocationRepository
from office_hero.repositories.mocks import InMemoryAuditService
from office_hero.repositories.route_repository import InMemoryRouteRepository
from office_hero.repositories.route_stop_repository import InMemoryRouteStopRepository
from office_hero.repositories.vehicle_crew_repository import InMemoryVehicleCrewRepository
from office_hero.repositories.vehicle_repository import InMemoryVehicleRepository
from office_hero.services.dispatch_service import DispatchService
from office_hero.services.job_service import JobService
from office_hero.services.schedule_suggestion_service import ScheduleSuggestionService
from office_hero.services.vehicle_crew_service import VehicleCrewService
from office_hero.services.vehicle_service import VehicleService


class _RouteTestAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.tenant_id = request.headers.get("X-Test-Tenant-Id")
        request.state.user_id = request.headers.get("X-Test-User-Id")
        request.state.role = request.headers.get("X-Test-Role", "dispatcher")
        perms = request.headers.get("X-Test-Permissions", "route:read,route:write")
        request.state.permissions = [p.strip() for p in perms.split(",") if p.strip()]
        return await call_next(request)


def _auth_headers() -> dict[str, str]:
    return {
        "X-Test-Tenant-Id": str(uuid4()),
        "X-Test-User-Id": str(uuid4()),
        "X-Test-Role": "dispatcher",
        "X-Test-Permissions": "route:read,route:write",
    }


@pytest.fixture
async def app_with_routes():
    """Create test app with route repositories pre-wired."""
    # Create repositories
    job_repo = InMemoryJobRepository()
    vehicle_repo = InMemoryVehicleRepository()
    vc_repo = InMemoryVehicleCrewRepository()
    route_repo = InMemoryRouteRepository()
    stop_repo = InMemoryRouteStopRepository()
    audit = InMemoryAuditService()

    # Create services
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

    # Create remaining services
    cust_repo = InMemoryCustomerRepository()
    loc_repo = InMemoryLocationRepository()
    job_svc = JobService(
        repo=job_repo,
        customer_repo=cust_repo,
        location_repo=loc_repo,
        audit=audit,
        template_registry=None,
    )
    vehicle_svc = VehicleService(repo=vehicle_repo, audit=audit, crew_repo=vc_repo)
    vc_svc = VehicleCrewService(
        crew_repo=vc_repo,
        vehicle_repo=vehicle_repo,
        user_repo=_NoopUserRepo(),
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
    )
    app.add_middleware(_RouteTestAuthMiddleware)
    return app, route_repo, stop_repo, dispatch_svc, job_repo, vehicle_repo, vc_repo


class _NoopUserRepo:
    async def get_by_id(self, user_id, tenant_id):
        return None


@pytest.mark.asyncio
async def test_list_routes_empty(app_with_routes):
    """GET /routes returns empty list on startup."""
    app, route_repo, _, _, _, _, _ = app_with_routes
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/routes",
            params={"date": str(date.today())},
            headers=_auth_headers(),
        )
    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["items"] == []


@pytest.mark.asyncio
async def test_get_route_not_found(app_with_routes):
    """GET /routes/{id} returns 404 for missing route."""
    app, _, _, _, _, _, _ = app_with_routes
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/routes/{uuid4()}",
            headers=_auth_headers(),
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_start_route_not_found(app_with_routes):
    """POST /routes/{id}/start returns 404 for missing route."""
    app, _, _, _, _, _, _ = app_with_routes
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/routes/{uuid4()}/start",
            headers=_auth_headers(),
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_route_not_found(app_with_routes):
    """POST /routes/{id}/cancel returns 404 for missing route."""
    app, _, _, _, _, _, _ = app_with_routes
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/routes/{uuid4()}/cancel",
            json={"reason": "Test cancellation"},
            headers=_auth_headers(),
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_mark_stop_arrived_not_found(app_with_routes):
    """POST /routes/{id}/stops/{stop_id}/arrived returns 404 for missing stop."""
    app, _, _, _, _, _, _ = app_with_routes
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/routes/{uuid4()}/stops/{uuid4()}/arrived",
            headers=_auth_headers(),
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_mark_stop_complete_not_found(app_with_routes):
    """POST /routes/{id}/stops/{stop_id}/complete returns 404 for missing stop."""
    app, _, _, _, _, _, _ = app_with_routes
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/routes/{uuid4()}/stops/{uuid4()}/complete",
            headers=_auth_headers(),
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_mark_stop_skip_not_found(app_with_routes):
    """POST /routes/{id}/stops/{stop_id}/skip returns 404 for missing stop."""
    app, _, _, _, _, _, _ = app_with_routes
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/routes/{uuid4()}/stops/{uuid4()}/skip",
            json={"reason": "Not available"},
            headers=_auth_headers(),
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_route_invalid_reason(app_with_routes):
    """POST /routes/{id}/cancel rejects reason < 3 chars."""
    app, _, _, _, _, _, _ = app_with_routes
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/routes/{uuid4()}/cancel",
            json={"reason": "ab"},
            headers=_auth_headers(),
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_skip_stop_invalid_reason(app_with_routes):
    """POST /routes/{id}/stops/{id}/skip rejects reason < 3 chars."""
    app, _, _, _, _, _, _ = app_with_routes
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/routes/{uuid4()}/stops/{uuid4()}/skip",
            json={"reason": "ab"},
            headers=_auth_headers(),
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_routes_with_date_filter(app_with_routes):
    """GET /routes respects date parameter."""
    app, _, _, _, _, _, _ = app_with_routes
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/routes",
            params={"date": "2026-06-15"},
            headers=_auth_headers(),
        )
    assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
