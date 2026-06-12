"""Job dispatch service — assign a vehicle and book a scheduled time slot.

The single public method ``dispatch`` handles the full atomic transition:
  pending → scheduled, with vehicle assignment and conflict detection.

When route repositories are wired (the production configuration), dispatching
also materialises the day's Route: the job is appended as a RouteStop on the
vehicle's route for ``scheduled_for.date()``, creating the route (with its
crew) if it doesn't exist yet.  This is what makes the admin "pick a suggested
slot" flow produce the same persistent Route/RouteStop records as the manual
``POST /routes`` commit path (Slice 14).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from office_hero.core.exceptions import (
    InvalidJobTransitionError,
    JobNotFoundError,
    RouteCommitConflictError,
    VehicleAlreadyBookedError,
    VehicleNotFoundError,
)
from office_hero.core.job_status import JobStatus, can_transition
from office_hero.core.logging import get_logger
from office_hero.core.route_status import RouteStatus
from office_hero.models.job import Job
from office_hero.repositories.job_repository import JobRepositoryProtocol
from office_hero.repositories.route_repository import RouteCreateRow
from office_hero.repositories.route_stop_repository import StopRow
from office_hero.repositories.vehicle_repository import VehicleRepositoryProtocol

log = get_logger(__name__)


class JobDispatchService:
    """Orchestrates the scheduling / dispatch of a job to a vehicle.

    ``route_repo`` / ``stop_repo`` / ``crew_repo`` are optional for unit tests
    that only exercise the job-state half; production wiring always passes
    them so dispatching keeps Routes in sync.
    """

    def __init__(
        self,
        job_repo: JobRepositoryProtocol,
        vehicle_repo: VehicleRepositoryProtocol,
        route_repo=None,
        stop_repo=None,
        crew_repo=None,
    ) -> None:
        self._job_repo = job_repo
        self._vehicle_repo = vehicle_repo
        self._route_repo = route_repo
        self._stop_repo = stop_repo
        self._crew_repo = crew_repo

    async def dispatch(
        self,
        tenant_id: UUID,
        job_id: UUID,
        *,
        vehicle_id: UUID,
        scheduled_for: datetime,
        user_id: UUID | None = None,
        travel_seconds: int = 0,
        distance_meters: int = 0,
    ) -> tuple[Job, UUID | None]:
        """Assign *vehicle_id* to *job_id*, schedule it, and sync the day's Route.

        Returns ``(job, route_id)`` — ``route_id`` is None when route
        repositories are not wired (unit-test configuration).

        Raises:
            JobNotFoundError: job doesn't exist in this tenant.
            VehicleNotFoundError: vehicle doesn't exist in this tenant.
            InvalidJobTransitionError: job is not in a dispatchable state.
            VehicleAlreadyBookedError: vehicle has an overlapping scheduled job.
            RouteCommitConflictError: vehicle has no crew for the date, or the
                route is already in_progress/complete/cancelled.
        """
        job = await self._job_repo.get_by_id(job_id, tenant_id)
        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found")

        vehicle = await self._vehicle_repo.get_by_id(vehicle_id, tenant_id)
        if vehicle is None:
            raise VehicleNotFoundError(f"Vehicle {vehicle_id} not found")

        current = JobStatus(job.status)
        if not can_transition(current, JobStatus.SCHEDULED):
            raise InvalidJobTransitionError(current, JobStatus.SCHEDULED)

        # Conflict check: any other scheduled job for this vehicle overlapping
        # the new slot (using the job's estimated duration as the window width).
        duration_min = job.estimated_duration_min or 60
        window_end = scheduled_for + timedelta(minutes=duration_min)
        conflicts = await self._job_repo.list_by_vehicle_in_window(
            tenant_id, vehicle_id, scheduled_for, window_end
        )
        # Exclude the job itself in case it is being re-dispatched to the same slot.
        conflicts = [c for c in conflicts if c.id != job_id]
        if conflicts:
            raise VehicleAlreadyBookedError(
                message=(
                    f"Vehicle {vehicle_id} is already booked around "
                    f"{scheduled_for.isoformat(timespec='minutes')}"
                ),
                vehicle_id=vehicle_id,
                scheduled_for=scheduled_for,
            )

        # Validate the route side BEFORE mutating the job so a crew/route
        # conflict leaves the job untouched.
        route = None
        crew = None
        existing_stops = []
        routes_wired = self._route_repo is not None and self._stop_repo is not None
        if routes_wired:
            work_date = scheduled_for.date()
            route = await self._route_repo.get_for_vehicle_date(tenant_id, vehicle_id, work_date)
            if route is not None:
                route_status = RouteStatus(route.status)
                if route_status in (
                    RouteStatus.IN_PROGRESS,
                    RouteStatus.COMPLETE,
                    RouteStatus.CANCELLED,
                ):
                    raise RouteCommitConflictError(
                        f"Route for this vehicle on {work_date} is already {route_status}",
                        reason=f"route_{route_status}",
                    )
                existing_stops = await self._stop_repo.get_for_route(tenant_id, route.id)
            else:
                if self._crew_repo is None:
                    raise RouteCommitConflictError(
                        "Crew repository not configured", reason="no_crew_repo"
                    )
                crew = await self._crew_repo.get_for_vehicle_date(
                    tenant_id, vehicle_id, work_date
                )
                if crew is None:
                    raise RouteCommitConflictError(
                        f"Vehicle {vehicle_id} has no crew assigned for {work_date}",
                        reason="no_crew",
                    )

        updated = await self._job_repo.update_fields(
            job_id,
            tenant_id,
            status=JobStatus.SCHEDULED.value,
            assigned_vehicle_id=vehicle_id,
            scheduled_for=scheduled_for,
        )

        route_id: UUID | None = None
        if routes_wired:
            if route is None:
                route = await self._route_repo.create(
                    tenant_id,
                    row=RouteCreateRow(
                        vehicle_id=vehicle_id,
                        vehicle_crew_id=crew.id,
                        work_date=scheduled_for.date(),
                        committed_by_user_id=user_id,
                        option_kind_applied="suggested",
                        notes=None,
                        total_distance_m=distance_meters,
                        total_duration_s=travel_seconds,
                    ),
                )
                inserted = await self._stop_repo.bulk_insert(
                    tenant_id,
                    route.id,
                    [
                        StopRow(
                            job_id=job_id,
                            sequence_index=0,
                            planned_eta=scheduled_for,
                            planned_distance_from_prev_m=distance_meters,
                            planned_duration_from_prev_s=travel_seconds,
                        )
                    ],
                )
                route.stops = inserted
            elif all(s.job_id != job_id for s in existing_stops):
                inserted = await self._stop_repo.bulk_insert(
                    tenant_id,
                    route.id,
                    [
                        StopRow(
                            job_id=job_id,
                            sequence_index=len(existing_stops),
                            planned_eta=scheduled_for,
                            planned_distance_from_prev_m=distance_meters,
                            planned_duration_from_prev_s=travel_seconds,
                        )
                    ],
                )
                route.stops = [*existing_stops, *inserted]
                await self._route_repo.update_totals(
                    route.id,
                    tenant_id,
                    total_distance_m=route.total_distance_m + distance_meters,
                    total_duration_s=route.total_duration_s + travel_seconds,
                )
            route_id = route.id

        log.info(
            "job.dispatched",
            job_id=str(job_id),
            vehicle_id=str(vehicle_id),
            scheduled_for=scheduled_for.isoformat(),
            route_id=str(route_id) if route_id else None,
            tenant_id=str(tenant_id),
        )
        return updated, route_id
