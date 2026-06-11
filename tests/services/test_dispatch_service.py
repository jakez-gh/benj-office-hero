"""Unit tests for DispatchService (Slice 14)."""

import pytest
from datetime import date
from uuid import uuid4
from office_hero.services.dispatch_service import DispatchService, DispatchCommitPayload
from office_hero.repositories.route_repository import InMemoryRouteRepository
from office_hero.repositories.route_stop_repository import InMemoryRouteStopRepository
from office_hero.repositories.job_repository import InMemoryJobRepository
from office_hero.repositories.vehicle_repository import InMemoryVehicleRepository
from office_hero.repositories.vehicle_crew_repository import InMemoryVehicleCrewRepository
from office_hero.repositories.mocks import InMemoryAuditService
from office_hero.services.schedule_suggestion_service import ScheduleSuggestionService
from office_hero.adapters.routing.stub import StubRoutingAdapter
from office_hero.models.job import Job
from office_hero.models.vehicle import Vehicle
from office_hero.models.vehicle_crew import VehicleCrew
from office_hero.core.job_status import JobStatus
from office_hero.core.exceptions import (
    RouteNotFoundError, InvalidRouteTransitionError,
    RouteCommitConflictError, ManualSequenceInvalidError,
)


@pytest.fixture
def service():
    """Create DispatchService with in-memory repositories."""
    job_repo = InMemoryJobRepository()
    vehicle_repo = InMemoryVehicleRepository()
    vc_repo = InMemoryVehicleCrewRepository()
    route_repo = InMemoryRouteRepository()
    stop_repo = InMemoryRouteStopRepository()
    audit = InMemoryAuditService()
    
    routing_adapter = StubRoutingAdapter()
    schedule_svc = ScheduleSuggestionService(
        job_repo=job_repo,
        vehicle_repo=vehicle_repo,
        routing_adapter=routing_adapter,
        vehicle_location_repo=None,
    )
    
    return DispatchService(
        route_repo=route_repo,
        stop_repo=stop_repo,
        job_repo=job_repo,
        vehicle_repo=vehicle_repo,
        vehicle_crew_repo=vc_repo,
        schedule_service=schedule_svc,
        audit=audit,
    ), (job_repo, vehicle_repo, vc_repo, route_repo, stop_repo)


@pytest.mark.asyncio
async def test_commit_dispatch_missing_crew(service):
    """commit_dispatch raises RouteCommitConflictError when vehicle has no crew."""
    svc, (job_repo, vehicle_repo, vc_repo, _, _) = service
    
    tenant_id = uuid4()
    user_id = uuid4()

    # Create job and vehicle but no crew
    job = await job_repo.create(
        tenant_id,
        customer_id=uuid4(),
        location_id=uuid4(),
        industry="generic",
        title="No-crew job",
        created_by_user_id=user_id,
    )
    job_id = job.id

    # Attach a geocoded location so schedule options can be computed
    # (mirrors the pattern in tests/unit/test_schedule_suggestion_service.py).
    from decimal import Decimal
    from types import SimpleNamespace

    original_get_by_id = job_repo.get_by_id

    async def get_by_id_with_location(jid, tid):
        result = await original_get_by_id(jid, tid)
        if result is not None:
            result.location = SimpleNamespace(
                lat=Decimal("41.8781"), lng=Decimal("-87.6298")
            )
        return result

    job_repo.get_by_id = get_by_id_with_location

    vehicle = await vehicle_repo.create(
        tenant_id, nickname="Van1", license_plate="ABC123"
    )
    
    payload = DispatchCommitPayload(
        date=date.today(),
        option_kind="nearest",
    )
    
    with pytest.raises(RouteCommitConflictError) as exc:
        await svc.commit_dispatch(tenant_id, user_id, job_id=job_id, payload=payload)
    assert exc.value.reason == "no_crew"


@pytest.mark.asyncio
async def test_list_routes_empty(service):
    """list_routes returns empty list on startup."""
    svc, _ = service
    
    routes = await svc.list_routes(uuid4(), date.today())
    assert routes == []


@pytest.mark.asyncio
async def test_get_route_not_found(service):
    """get_route raises RouteNotFoundError when route doesn't exist."""
    svc, _ = service
    
    with pytest.raises(RouteNotFoundError):
        await svc.get_route(uuid4(), uuid4())


@pytest.mark.asyncio
async def test_mark_stop_arrived_not_found(service):
    """mark_stop_arrived raises RouteNotFoundError when stop doesn't exist."""
    svc, _ = service
    
    with pytest.raises(RouteNotFoundError):
        await svc.mark_stop_arrived(uuid4(), uuid4(), uuid4())


@pytest.mark.asyncio
async def test_mark_stop_complete_not_found(service):
    """mark_stop_complete raises RouteNotFoundError when stop doesn't exist."""
    svc, _ = service
    
    with pytest.raises(RouteNotFoundError):
        await svc.mark_stop_complete(uuid4(), uuid4(), uuid4())


@pytest.mark.asyncio
async def test_cancel_route_not_found(service):
    """cancel_route raises RouteNotFoundError when route doesn't exist."""
    svc, _ = service
    
    with pytest.raises(RouteNotFoundError):
        await svc.cancel_route(uuid4(), uuid4(), uuid4(), reason="Emergency")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
