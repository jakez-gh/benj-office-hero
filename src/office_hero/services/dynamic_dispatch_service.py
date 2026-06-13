"""DynamicDispatchService — day-of re-routing for sick-days and emergencies (Slice 16).

Closes the original concept's "adapting to real-world events" clause. Builds on the
Slice-14 Route/RouteStop store and the Slice-13 schedule suggestions; shares all repos
with the existing dispatch services.

Two operations matching the concept's two named day-of events:
- ``reassign_route``    — a vehicle/technician goes down: move its pending stops to
  another vehicle's route for the day and finalise the source route.
- ``add_emergency_job`` — an urgent job arrives: drop it into the best (or chosen)
  vehicle's route ahead of that route's still-pending work.

(Routed-job-cancellation cleanup is deferred — see the slice design.)

Single-instance concurrency assumption (same as contract generation); two simultaneous
reassigns of one route can race — documented in the slice design.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from office_hero.core.exceptions import (
    JobNotFoundError,
    RouteCommitConflictError,
    RouteNotFoundError,
    VehicleNotFoundError,
)
from office_hero.core.job_status import JobStatus
from office_hero.core.logging import get_logger
from office_hero.core.route_status import (
    RouteStatus,
    RouteStopStatus,
    is_terminal_route,
    is_terminal_stop,
)
from office_hero.models.route import Route
from office_hero.repositories.route_repository import RouteCreateRow
from office_hero.repositories.route_stop_repository import StopRow

log = get_logger(__name__)


class DynamicDispatchService:
    """Day-of re-routing operations over committed Routes."""

    def __init__(
        self,
        route_repo,
        stop_repo,
        job_repo,
        vehicle_repo,
        vehicle_crew_repo,
        schedule_service=None,
        audit=None,
    ) -> None:
        self._route_repo = route_repo
        self._stop_repo = stop_repo
        self._job_repo = job_repo
        self._vehicle_repo = vehicle_repo
        self._crew_repo = vehicle_crew_repo
        self._schedule_svc = schedule_service
        self._audit = audit

    # ------------------------------------------------------------------
    # 1. Reassign a route (vehicle / technician down)
    # ------------------------------------------------------------------

    async def reassign_route(
        self,
        tenant_id: UUID,
        user_id: UUID,
        route_id: UUID,
        *,
        target_vehicle_id: UUID,
    ) -> dict[str, Any]:
        """Move the source route's pending stops to ``target_vehicle_id`` for the day.

        Terminal stops (arrived/complete/skipped) stay on the source as history. The
        source route is finalised (``complete`` if it had completed work, else
        ``cancelled``). Returns ``{source_route, target_route, moved_count}``.
        """
        source = await self._route_repo.get_by_id(route_id, tenant_id)
        if source is None:
            raise RouteNotFoundError(f"Route {route_id} not found")
        src_status = RouteStatus(source.status)
        if is_terminal_route(src_status):
            raise RouteCommitConflictError(
                f"Route is {src_status} and cannot be reassigned", reason=f"route_{src_status}"
            )
        if target_vehicle_id == source.vehicle_id:
            raise RouteCommitConflictError(
                "Target vehicle is the same as the source vehicle", reason="same_vehicle"
            )

        target_vehicle = await self._vehicle_repo.get_by_id(target_vehicle_id, tenant_id)
        if target_vehicle is None:
            raise VehicleNotFoundError(f"Vehicle {target_vehicle_id} not found")

        work_date = source.work_date
        crew = await self._crew_repo.get_for_vehicle_date(tenant_id, target_vehicle_id, work_date)
        if crew is None:
            raise RouteCommitConflictError(
                f"Vehicle {target_vehicle_id} has no crew assigned for {work_date}",
                reason="no_crew",
            )

        src_stops = await self._stop_repo.get_for_route(tenant_id, route_id)
        pending = [s for s in src_stops if not is_terminal_stop(RouteStopStatus(s.status))]
        if not pending:
            raise RouteCommitConflictError(
                "Route has no pending stops to reassign", reason="nothing_to_reassign"
            )

        target = await self._route_repo.get_for_vehicle_date(
            tenant_id, target_vehicle_id, work_date
        )
        if target is not None and is_terminal_route(RouteStatus(target.status)):
            raise RouteCommitConflictError(
                f"Target route is already {target.status}", reason="target_terminal"
            )

        existing_target_stops = []
        if target is None:
            target = await self._route_repo.create(
                tenant_id,
                row=RouteCreateRow(
                    vehicle_id=target_vehicle_id,
                    vehicle_crew_id=crew.id,
                    work_date=work_date,
                    committed_by_user_id=user_id,
                    option_kind_applied="reassigned",
                    notes=f"reassigned from route {route_id}",
                    total_distance_m=0,
                    total_duration_s=0,
                ),
            )
        else:
            existing_target_stops = await self._stop_repo.get_for_route(tenant_id, target.id)

        base_idx = len(existing_target_stops)
        new_rows = [
            StopRow(
                job_id=s.job_id,
                sequence_index=base_idx + i,
                planned_eta=s.planned_eta,
                planned_distance_from_prev_m=s.planned_distance_from_prev_m,
                planned_duration_from_prev_s=s.planned_duration_from_prev_s,
            )
            for i, s in enumerate(pending)
        ]
        inserted = await self._stop_repo.bulk_insert(tenant_id, target.id, new_rows)
        add_dist = sum(s.planned_distance_from_prev_m for s in pending)
        add_dur = sum(s.planned_duration_from_prev_s for s in pending)
        target = await self._route_repo.update_totals(
            target.id,
            tenant_id,
            total_distance_m=target.total_distance_m + add_dist,
            total_duration_s=target.total_duration_s + add_dur,
        )
        target.stops = [*existing_target_stops, *inserted]

        # Skip the moved stops on the source, then finalise the source route.
        for s in pending:
            await self._stop_repo.update_status(s.id, tenant_id, RouteStopStatus.SKIPPED)

        remaining = await self._stop_repo.get_for_route(tenant_id, route_id)
        has_completed = any(
            RouteStopStatus(s.status) == RouteStopStatus.COMPLETE for s in remaining
        )
        now = datetime.now(UTC)
        if src_status == RouteStatus.IN_PROGRESS and has_completed:
            source = await self._route_repo.update_status(
                route_id, tenant_id, RouteStatus.COMPLETE, completed_at=now
            )
        else:
            source = await self._route_repo.update_status(
                route_id,
                tenant_id,
                RouteStatus.CANCELLED,
                cancelled_at=now,
                cancel_reason=f"reassigned to vehicle {target_vehicle_id}",
            )
        source.stops = remaining

        await self._emit(
            "route.reassigned",
            {
                "source_route_id": str(route_id),
                "target_route_id": str(target.id),
                "target_vehicle_id": str(target_vehicle_id),
                "moved_count": len(pending),
            },
            tenant_id,
            user_id,
        )
        log.info(
            "route.reassigned",
            source_route_id=str(route_id),
            target_route_id=str(target.id),
            moved_count=len(pending),
            tenant_id=str(tenant_id),
        )
        return {"source_route": source, "target_route": target, "moved_count": len(pending)}

    # ------------------------------------------------------------------
    # 2. Emergency dispatch (urgent job jumps the line)
    # ------------------------------------------------------------------

    async def add_emergency_job(
        self,
        tenant_id: UUID,
        user_id: UUID,
        job_id: UUID,
        *,
        window_start: datetime,
        window_end: datetime,
        target_vehicle_id: UUID | None = None,
    ) -> Route:
        """Insert an emergency job ahead of a vehicle's pending stops; return the route.

        Resolves the vehicle from ``target_vehicle_id`` or the top-ranked schedule
        suggestion. The job lands at the front of the pending queue (after any
        arrived/in-progress stop) and transitions to ``scheduled``.
        """
        job = await self._job_repo.get_by_id(job_id, tenant_id)
        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found")
        if job.status != JobStatus.PENDING:
            raise RouteCommitConflictError(
                f"Job {job_id} is {job.status} and cannot be emergency-dispatched",
                reason="job_not_pending",
            )

        travel_s = 0
        dist_m = 0
        if target_vehicle_id is None:
            if self._schedule_svc is None:
                raise RouteCommitConflictError(
                    "No target vehicle and no schedule service to pick one",
                    reason="no_options",
                )
            options = await self._schedule_svc.get_options(
                tenant_id,
                job_id,
                window_start=window_start,
                window_end=window_end,
                max_results=1,
            )
            if not options:
                raise RouteCommitConflictError(
                    "No vehicle available for emergency dispatch", reason="no_options"
                )
            target_vehicle_id = options[0].vehicle_id
            travel_s = options[0].travel_seconds
            dist_m = options[0].distance_meters
        else:
            vehicle = await self._vehicle_repo.get_by_id(target_vehicle_id, tenant_id)
            if vehicle is None:
                raise VehicleNotFoundError(f"Vehicle {target_vehicle_id} not found")

        work_date = window_start.date()
        crew = await self._crew_repo.get_for_vehicle_date(tenant_id, target_vehicle_id, work_date)
        if crew is None:
            raise RouteCommitConflictError(
                f"Vehicle {target_vehicle_id} has no crew assigned for {work_date}",
                reason="no_crew",
            )

        route = await self._route_repo.get_for_vehicle_date(tenant_id, target_vehicle_id, work_date)
        if route is not None and is_terminal_route(RouteStatus(route.status)):
            raise RouteCommitConflictError(
                f"Target route is already {route.status}", reason="target_terminal"
            )

        if route is None:
            route = await self._route_repo.create(
                tenant_id,
                row=RouteCreateRow(
                    vehicle_id=target_vehicle_id,
                    vehicle_crew_id=crew.id,
                    work_date=work_date,
                    committed_by_user_id=user_id,
                    option_kind_applied="emergency",
                    notes=None,
                    total_distance_m=dist_m,
                    total_duration_s=travel_s,
                ),
            )
            existing = []
        else:
            existing = await self._stop_repo.get_for_route(tenant_id, route.id)

        # Insert ahead of the first still-pending stop (jump the line) but never
        # before an arrived/in-progress stop a technician is already working.
        insert_pos = next(
            (
                i
                for i, s in enumerate(existing)
                if RouteStopStatus(s.status) == RouteStopStatus.PENDING
            ),
            len(existing),
        )
        ordered = existing[:insert_pos] + [None] + existing[insert_pos:]
        await self._stop_repo.replace_all(
            tenant_id,
            route.id,
            [
                (
                    StopRow(
                        job_id=job_id,
                        sequence_index=i,
                        planned_eta=window_start,
                        planned_distance_from_prev_m=dist_m,
                        planned_duration_from_prev_s=travel_s,
                    )
                    if s is None
                    else StopRow(
                        job_id=s.job_id,
                        sequence_index=i,
                        planned_eta=s.planned_eta,
                        planned_distance_from_prev_m=s.planned_distance_from_prev_m,
                        planned_duration_from_prev_s=s.planned_duration_from_prev_s,
                    )
                )
                for i, s in enumerate(ordered)
            ],
        )
        # Restore non-pending statuses that replace_all reset (preserve real progress).
        rebuilt = await self._stop_repo.get_for_route(tenant_id, route.id)
        by_job = {s.job_id: s for s in existing}
        for new_stop in rebuilt:
            old = by_job.get(new_stop.job_id)
            if old is not None and RouteStopStatus(old.status) != RouteStopStatus.PENDING:
                await self._stop_repo.update_status(
                    new_stop.id,
                    tenant_id,
                    old.status,
                    arrived_at=old.actual_arrived_at,
                    completed_at=old.actual_completed_at,
                )

        await self._job_repo.update_fields(
            job_id,
            tenant_id,
            status=JobStatus.SCHEDULED.value,
            assigned_vehicle_id=target_vehicle_id,
            scheduled_for=window_start,
        )

        route = await self._route_repo.get_by_id(route.id, tenant_id)
        route.stops = await self._stop_repo.get_for_route(tenant_id, route.id)

        await self._emit(
            "job.emergency_dispatched",
            {
                "job_id": str(job_id),
                "route_id": str(route.id),
                "vehicle_id": str(target_vehicle_id),
                "inserted_at": insert_pos,
            },
            tenant_id,
            user_id,
        )
        log.info(
            "job.emergency_dispatched",
            job_id=str(job_id),
            route_id=str(route.id),
            vehicle_id=str(target_vehicle_id),
            tenant_id=str(tenant_id),
        )
        return route

    # NOTE: routed-job cancellation cleanup (skip the open stop + finalise the route
    # when a job already on a route is cancelled) is deferred — it needs a
    # repo lookup "routes containing job" and a JobService callback seam. Tracked as
    # future work in the slice design; reassign + emergency are the concept's headline
    # events.

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _emit(self, event_type: str, details: dict, tenant_id: UUID, user_id: UUID) -> None:
        if self._audit is not None:
            await self._audit.log_event(
                event_type=event_type, details=details, tenant_id=tenant_id, user_id=user_id
            )
