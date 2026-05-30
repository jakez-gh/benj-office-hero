"""Unit tests for ScheduleSuggestionService (TDD-first, no DB)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from office_hero.adapters.routing.protocol import RouteResult
from office_hero.adapters.routing.stub import StubRoutingAdapter
from office_hero.core.exceptions import JobNotFoundError, SchedulingNotAvailableError
from office_hero.repositories.job_repository import InMemoryJobRepository
from office_hero.repositories.vehicle_repository import InMemoryVehicleRepository
from office_hero.services.schedule_suggestion_service import ScheduleSuggestionService


@dataclass
class _FakeLocation:
    """Minimal location stand-in so unit tests stay off SQLAlchemy machinery."""

    lat: Decimal | None
    lng: Decimal | None
    geocode_status: str = "complete"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tenant_id():
    return uuid4()


@pytest.fixture()
def user_id():
    return uuid4()


@pytest.fixture()
def j_repo():
    return InMemoryJobRepository()


@pytest.fixture()
def v_repo():
    return InMemoryVehicleRepository()


@pytest.fixture()
def routing():
    return StubRoutingAdapter()


@pytest.fixture()
def service(j_repo, v_repo, routing):
    return ScheduleSuggestionService(
        job_repo=j_repo,
        vehicle_repo=v_repo,
        routing_adapter=routing,
    )


def _window():
    start = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
    end = datetime(2026, 6, 1, 17, 0, tzinfo=UTC)
    return start, end


def _make_location(*, lat=None, lng=None, geocode_status="complete") -> _FakeLocation:
    from decimal import Decimal

    return _FakeLocation(
        lat=Decimal(str(lat)) if lat is not None else None,
        lng=Decimal(str(lng)) if lng is not None else None,
        geocode_status=geocode_status,
    )


async def _make_job(j_repo, tenant_id, user_id, *, location=None):
    """Create a job and patch get_by_id so the service sees the right location."""
    job = await j_repo.create(
        tenant_id,
        customer_id=uuid4(),
        location_id=uuid4(),
        industry="plumbing",
        title="Fix leak",
        created_by_user_id=user_id,
    )
    loc = location if location is not None else _make_location(lat=41.8781, lng=-87.6298)

    original_get = j_repo.get_by_id
    jid = job.id

    async def _patched_get(job_id, t_id):
        result = await original_get(job_id, t_id)
        if result is not None and result.id == jid:
            result.location = loc
        return result

    j_repo.get_by_id = _patched_get
    return job


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_job_not_found_raises(service, tenant_id):
    """get_options raises JobNotFoundError for an unknown job."""
    start, end = _window()
    with pytest.raises(JobNotFoundError):
        await service.get_options(tenant_id, uuid4(), window_start=start, window_end=end)


async def test_location_not_geocoded_raises(service, j_repo, tenant_id, user_id):
    """get_options raises SchedulingNotAvailableError when coords are absent."""
    job = await _make_job(j_repo, tenant_id, user_id, location=_make_location(lat=None, lng=None))
    start, end = _window()
    with pytest.raises(SchedulingNotAvailableError, match="not been geocoded"):
        await service.get_options(tenant_id, job.id, window_start=start, window_end=end)


async def test_no_vehicles_returns_empty(service, j_repo, tenant_id, user_id):
    """get_options returns [] when no vehicles exist."""
    job = await _make_job(j_repo, tenant_id, user_id)
    start, end = _window()
    result = await service.get_options(tenant_id, job.id, window_start=start, window_end=end)
    assert result == []


async def test_all_vehicles_busy_returns_empty(service, j_repo, v_repo, tenant_id, user_id):
    """get_options returns [] when every vehicle is busy in the window."""
    vehicle = await v_repo.create(
        tenant_id,
        license_plate="BUSY-001",
        home_base_lat=41.8,
        home_base_lng=-87.6,
    )
    job = await _make_job(j_repo, tenant_id, user_id)

    # Create a conflicting job assigned to the vehicle
    start, end = _window()
    blocking_job = await j_repo.create(
        tenant_id,
        customer_id=uuid4(),
        location_id=uuid4(),
        industry="plumbing",
        title="Blocking job",
        created_by_user_id=user_id,
    )
    # Manually assign and schedule so it overlaps
    blocking_job_row = j_repo._rows[blocking_job.id]
    blocking_job_row["assigned_vehicle_id"] = vehicle.id
    blocking_job_row["status"] = "scheduled"
    blocking_job_row["scheduled_for"] = start + timedelta(hours=1)
    blocking_job_row["estimated_duration_min"] = 120

    result = await service.get_options(tenant_id, job.id, window_start=start, window_end=end)
    assert result == []


async def test_two_free_vehicles_sorted_by_travel_time(j_repo, v_repo, tenant_id, user_id):
    """Two free vehicles → 2 options sorted by travel_seconds ASC."""

    class _VariableRouter:
        """Returns different times per vehicle to test sorting."""

        def __init__(self):
            self._calls: list[tuple[float, float, float, float]] = []

        async def get_route(self, from_lat, from_lng, to_lat, to_lng):
            self._calls.append((from_lat, from_lng, to_lat, to_lng))
            # Use from_lat as a proxy: higher lat → longer trip
            duration = 600 if from_lat < 40.0 else 1200
            return RouteResult(duration_seconds=duration, distance_meters=duration * 10)

    router = _VariableRouter()
    svc = ScheduleSuggestionService(
        job_repo=j_repo,
        vehicle_repo=v_repo,
        routing_adapter=router,
    )

    # vehicle A: lat 39 → 600 s (closer)
    await v_repo.create(
        tenant_id,
        license_plate="CLOSE-001",
        nickname="Close Van",
        home_base_lat=39.0,
        home_base_lng=-87.0,
    )
    # vehicle B: lat 41 → 1200 s (farther)
    await v_repo.create(
        tenant_id,
        license_plate="FAR-002",
        home_base_lat=41.0,
        home_base_lng=-87.0,
    )

    job = await _make_job(j_repo, tenant_id, user_id)
    start, end = _window()

    options = await svc.get_options(tenant_id, job.id, window_start=start, window_end=end)

    assert len(options) == 2
    assert options[0].travel_seconds < options[1].travel_seconds
    assert options[0].rank == 1
    assert options[1].rank == 2
    assert options[0].vehicle_display == "Close Van (CLOSE-001)"
    assert options[1].vehicle_display == "FAR-002"


async def test_max_results_caps_output(j_repo, v_repo, tenant_id, user_id):
    """max_results=1 caps output at 1 even if 3 vehicles are free."""
    for i in range(3):
        await v_repo.create(
            tenant_id,
            license_plate=f"MULTI-{i:03d}",
            home_base_lat=40.0 + i,
            home_base_lng=-87.0,
        )
    job = await _make_job(j_repo, tenant_id, user_id)
    start, end = _window()
    svc = ScheduleSuggestionService(
        job_repo=j_repo,
        vehicle_repo=v_repo,
        routing_adapter=StubRoutingAdapter(),
    )
    options = await svc.get_options(
        tenant_id, job.id, window_start=start, window_end=end, max_results=1
    )
    assert len(options) == 1


async def test_suggested_start_rounded_to_15_minutes(j_repo, v_repo, tenant_id, user_id):
    """suggested_start is rounded up to the next 15-minute boundary."""

    class _OddRouter:
        async def get_route(self, from_lat, from_lng, to_lat, to_lng):
            return RouteResult(duration_seconds=600, distance_meters=5000)

    svc = ScheduleSuggestionService(
        job_repo=j_repo,
        vehicle_repo=v_repo,
        routing_adapter=_OddRouter(),
    )
    await v_repo.create(tenant_id, license_plate="ROUND-001")
    job = await _make_job(j_repo, tenant_id, user_id)

    # window_start at 09:07 → arrival at 09:17 → round to 09:30
    start = datetime(2026, 6, 1, 9, 7, tzinfo=UTC)
    end = datetime(2026, 6, 1, 17, 0, tzinfo=UTC)
    options = await svc.get_options(tenant_id, job.id, window_start=start, window_end=end)

    assert len(options) == 1
    assert options[0].suggested_start.minute == 30


async def test_live_gps_position_used_when_available(j_repo, v_repo, tenant_id, user_id):
    """ScheduleSuggestionService uses the latest GPS fix over home_base coords."""
    from decimal import Decimal

    from office_hero.repositories.vehicle_location_repository import (
        InMemoryVehicleLocationRepository,
    )

    loc_repo = InMemoryVehicleLocationRepository()
    called_with: list[tuple[float, float]] = []

    class _CapturingRouter:
        async def get_route(self, from_lat, from_lng, to_lat, to_lng):
            called_with.append((from_lat, from_lng))
            return RouteResult(duration_seconds=300, distance_meters=2000)

    svc = ScheduleSuggestionService(
        job_repo=j_repo,
        vehicle_repo=v_repo,
        routing_adapter=_CapturingRouter(),
        vehicle_location_repo=loc_repo,
    )

    vehicle = await v_repo.create(tenant_id, license_plate="GPS-001")
    job = await _make_job(j_repo, tenant_id, user_id)

    # Post a GPS fix far from home base
    gps_lat, gps_lng = 51.5074, -0.1278
    await loc_repo.create(
        tenant_id,
        vehicle.id,
        lat=Decimal(str(gps_lat)),
        lng=Decimal(str(gps_lng)),
        accuracy_m=None,
        recorded_at=datetime(2026, 6, 1, 8, 0, tzinfo=UTC),
    )

    start, end = _window()
    options = await svc.get_options(tenant_id, job.id, window_start=start, window_end=end)

    assert len(options) == 1
    assert called_with[0][0] == pytest.approx(gps_lat)
    assert called_with[0][1] == pytest.approx(gps_lng)
