"""ScheduleSuggestionService — core of the Slice-13 routing MVP.

Given a job and a time window, returns 2-3 ranked :class:`ScheduleOption`
objects showing which vehicles are free and how long it would take each
one to reach the job site.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from office_hero.adapters.routing.protocol import RoutingAdapter
from office_hero.core.exceptions import JobNotFoundError, SchedulingNotAvailableError


@dataclass
class ScheduleOption:
    """A ranked appointment slot for one vehicle."""

    vehicle_id: UUID
    vehicle_display: str
    suggested_start: datetime
    travel_seconds: int
    distance_meters: int
    rank: int


def _round_up_15(dt: datetime) -> datetime:
    """Round *dt* up to the next 15-minute boundary (or return as-is if already on one)."""
    minute = dt.minute
    remainder = minute % 15
    if remainder == 0 and dt.second == 0 and dt.microsecond == 0:
        return dt
    delta = timedelta(minutes=(15 - remainder), seconds=-dt.second, microseconds=-dt.microsecond)
    return dt + delta


class ScheduleSuggestionService:
    """Produce ranked schedule suggestions for a job within a time window.

    Depends on repository protocols (ADR 058) and a pluggable routing adapter.
    All arguments are injected so unit tests can pass in-memory mocks.
    """

    def __init__(
        self,
        job_repo,
        vehicle_repo,
        routing_adapter: RoutingAdapter,
        clock=None,
    ) -> None:
        self._job_repo = job_repo
        self._vehicle_repo = vehicle_repo
        self._routing = routing_adapter
        self._clock = clock or (lambda: datetime.now(UTC))

    async def get_options(
        self,
        tenant_id: UUID,
        job_id: UUID,
        *,
        window_start: datetime,
        window_end: datetime,
        max_results: int = 3,
    ) -> list[ScheduleOption]:
        """Return up to *max_results* ranked options, sorted by travel time ASC.

        Raises:
            JobNotFoundError: if the job does not exist within *tenant_id*.
            SchedulingNotAvailableError: if the job location has no geocoords.
        """
        job = await self._job_repo.get_by_id(job_id, tenant_id)
        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found")

        location = job.location
        if location is None or location.lat is None or location.lng is None:
            raise SchedulingNotAvailableError("Job location has not been geocoded yet.")

        job_lat = float(location.lat)
        job_lng = float(location.lng)

        vehicles = await self._vehicle_repo.list_active(tenant_id)

        candidates: list[tuple[int, int, object]] = []

        for vehicle in vehicles:
            busy_jobs = await self._job_repo.list_by_vehicle_in_window(
                tenant_id, vehicle.id, window_start, window_end
            )
            if busy_jobs:
                continue

            from_lat = float(vehicle.home_base_lat) if vehicle.home_base_lat is not None else 0.0
            from_lng = float(vehicle.home_base_lng) if vehicle.home_base_lng is not None else 0.0

            route = await self._routing.get_route(from_lat, from_lng, job_lat, job_lng)
            if route is None:
                continue

            candidates.append((route.duration_seconds, route.distance_meters, vehicle))

        candidates.sort(key=lambda t: t[0])

        options: list[ScheduleOption] = []
        for rank, (duration_s, distance_m, vehicle) in enumerate(candidates[:max_results], start=1):
            arrival = window_start + timedelta(seconds=duration_s)
            suggested_start = _round_up_15(arrival)

            if vehicle.nickname:
                display = f"{vehicle.nickname} ({vehicle.license_plate})"
            else:
                display = vehicle.license_plate

            options.append(
                ScheduleOption(
                    vehicle_id=vehicle.id,
                    vehicle_display=display,
                    suggested_start=suggested_start,
                    travel_seconds=duration_s,
                    distance_meters=distance_m,
                    rank=rank,
                )
            )

        return options
