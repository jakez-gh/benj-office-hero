"""DispatchService â€” commits routing options into persistent Routes (Slice 14).

All DB mutations in commit_dispatch happen inside a single logical transaction
so partial failure rolls back cleanly. The routing adapter is called BEFORE any
DB writes to ensure a network failure cannot corrupt half-committed state.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from office_hero.core.exceptions import (
    InvalidRouteTransitionError,
    ManualSequenceInvalidError,
    RouteCommitConflictError,
    RouteNotFoundError,
)
from office_hero.core.job_status import JobStatus
from office_hero.core.logging import get_logger
from office_hero.core.route_status import (
    RouteStatus,
    RouteStopStatus,
    can_route_transition,
    can_stop_transition,
    is_terminal_stop,
)
from office_hero.models.route import Route, RouteStop
from office_hero.repositories.route_repository import (
    InMemoryRouteRepository,
    RouteCreateRow,
    RouteRepositoryProtocol,
)
from office_hero.repositories.route_stop_repository import (
    InMemoryRouteStopRepository,
    RouteStopRepositoryProtocol,
    StopRow,
)

log = get_logger(__name__)

OptionKind = Literal["nearest", "earliest", "balanced"]


@dataclass
class DispatchCommitPayload:
    """Validated payload for commit_dispatch â€” exactly one of option_kind or manual_* set."""

    date: "datetime.date"  # noqa: UP037 â€” avoid circular import with datetime module alias
    option_kind: OptionKind | None = None
    manual_vehicle_id: UUID | None = None
    manual_sequence: list[UUID] | None = None
    notes: str | None = None


class DispatchService:
    """Commit routing options into persistent Route + RouteStop rows.

    NOTE: No back-office push in this slice. Outbox/Saga integration for
    pushing committed routes to ServiceTitan/PestPac is deferred to Slice 25+.
    """

    def __init__(
        self,
        route_repo: RouteRepositoryProtocol,
        stop_repo: RouteStopRepositoryProtocol,
        job_repo,
        vehicle_repo,
        vehicle_crew_repo,
        schedule_service,
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
    # Primary dispatch entry point
    # ------------------------------------------------------------------

    async def commit_dispatch(
        self,
        tenant_id: UUID,
        user_id: UUID,
        *,
        job_id: UUID,
        payload: DispatchCommitPayload,
    ) -> Route:
        """Commit a dispatch, creating or replacing a Route for the vehicle/day.

        Raises:
            RouteCommitConflictError: vehicle has no crew, route is in_progress/complete,
                or target job is already complete/cancelled.
            ManualSequenceInvalidError: manual sequence has duplicates, missing target job,
                or references unknown/invalid jobs.
        """
        # 1. Resolve vehicle_id and ordered job sequence (before any DB writes)
        if payload.option_kind is not None:
            vehicle_id, stop_rows = await self._resolve_option_mode(tenant_id, job_id, payload)
        else:
            vehicle_id, stop_rows = await self._resolve_manual_mode(tenant_id, job_id, payload)

        work_date = payload.date

        # 2. Validate target job is dispatchable
        target_job = await self._job_repo.get_by_id(job_id, tenant_id)
        if target_job is None:
            raise RouteCommitConflictError(f"Job {job_id} not found", reason="job_not_found")
        if target_job.status in (JobStatus.COMPLETE, JobStatus.CANCELLED):
            raise RouteCommitConflictError(
                f"Job {job_id} is {target_job.status} and cannot be dispatched",
                reason="job_terminal",
            )

        # 3. Resolve crew for this vehicle/date
        crew = await self._crew_repo.get_for_vehicle_date(tenant_id, vehicle_id, work_date)
        if crew is None:
            raise RouteCommitConflictError(
                f"Vehicle {vehicle_id} has no crew assigned for {work_date}",
                reason="no_crew",
            )

        # 4. Look up or create the Route
        existing_route = await self._route_repo.get_for_vehicle_date(
            tenant_id, vehicle_id, work_date
        )

        if existing_route is not None:
            status = RouteStatus(existing_route.status)
            if status in (RouteStatus.IN_PROGRESS, RouteStatus.COMPLETE, RouteStatus.CANCELLED):
                raise RouteCommitConflictError(
                    f"Route is already {status} and cannot be re-dispatched",
                    reason=f"route_{status}",
                )
            # Idempotency check: same sequence â†’ no-op (fetch stops explicitly)
            existing_stops = await self._stop_repo.get_for_route(tenant_id, existing_route.id)
            current_job_ids = [s.job_id for s in existing_stops]
            requested_job_ids = [s.job_id for s in stop_rows]
            if current_job_ids == requested_job_ids:
                log.info("dispatch.idempotent", route_id=str(existing_route.id))
                existing_route.stops = existing_stops
                return existing_route

            # Replace stops atomically
            new_stops = await self._stop_repo.replace_all(tenant_id, existing_route.id, stop_rows)
            existing_route.stops = new_stops
            total_dist = sum(s.planned_distance_from_prev_m for s in stop_rows)
            total_dur = sum(s.planned_duration_from_prev_s for s in stop_rows)
            route = await self._route_repo.update_totals(
                existing_route.id,
                tenant_id,
                total_distance_m=total_dist,
                total_duration_s=total_dur,
            )
            route.stops = new_stops
        else:
            total_dist = sum(s.planned_distance_from_prev_m for s in stop_rows)
            total_dur = sum(s.planned_duration_from_prev_s for s in stop_rows)
            route = await self._route_repo.create(
                tenant_id,
                row=RouteCreateRow(
                    vehicle_id=vehicle_id,
                    vehicle_crew_id=crew.id,
                    work_date=work_date,
                    committed_by_user_id=user_id,
                    option_kind_applied=payload.option_kind or "manual",
                    notes=payload.notes,
                    total_distance_m=total_dist,
                    total_duration_s=total_dur,
                ),
            )
            new_stops = await self._stop_repo.bulk_insert(tenant_id, route.id, stop_rows)
            route.stops = new_stops

        # 5. Transition target job to scheduled if pending
        if target_job.status == JobStatus.PENDING:
            await self._job_repo.update_fields(job_id, tenant_id, status=JobStatus.SCHEDULED)

        log.info(
            "dispatch.committed",
            route_id=str(route.id),
            vehicle_id=str(vehicle_id),
            work_date=str(work_date),
            stop_count=len(stop_rows),
            tenant_id=str(tenant_id),
        )
        return route

    # ------------------------------------------------------------------
    # Route lifecycle
    # ------------------------------------------------------------------

    async def start_route(self, tenant_id: UUID, user_id: UUID, route_id: UUID) -> Route:
        """Transition route from committed â†’ in_progress."""
        route = await self._route_repo.get_by_id(route_id, tenant_id)
        if route is None:
            raise RouteNotFoundError(f"Route {route_id} not found")
        from_status = RouteStatus(route.status)
        if not can_route_transition(from_status, RouteStatus.IN_PROGRESS):
            raise InvalidRouteTransitionError(str(from_status), str(RouteStatus.IN_PROGRESS))
        return await self._route_repo.update_status(
            route_id,
            tenant_id,
            RouteStatus.IN_PROGRESS,
            started_at=datetime.now(UTC),
        )

    async def cancel_route(
        self, tenant_id: UUID, user_id: UUID, route_id: UUID, *, reason: str
    ) -> Route:
        """Cancel a route, skipping all non-terminal stops and returning scheduled jobs to pending."""
        route = await self._route_repo.get_by_id(route_id, tenant_id)
        if route is None:
            raise RouteNotFoundError(f"Route {route_id} not found")
        from_status = RouteStatus(route.status)
        if not can_route_transition(from_status, RouteStatus.CANCELLED):
            raise InvalidRouteTransitionError(str(from_status), str(RouteStatus.CANCELLED))

        stops = await self._stop_repo.get_for_route(tenant_id, route_id)
        affected = 0
        for stop in stops:
            if not is_terminal_stop(RouteStopStatus(stop.status)):
                await self._stop_repo.update_status(stop.id, tenant_id, RouteStopStatus.SKIPPED)
                # Return scheduled jobs to pending
                job = await self._job_repo.get_by_id(stop.job_id, tenant_id)
                if job is not None and job.status == JobStatus.SCHEDULED:
                    await self._job_repo.update_fields(
                        stop.job_id, tenant_id, status=JobStatus.PENDING
                    )
                affected += 1

        route = await self._route_repo.update_status(
            route_id,
            tenant_id,
            RouteStatus.CANCELLED,
            cancelled_at=datetime.now(UTC),
            cancel_reason=reason,
        )
        log.info(
            "route.cancelled",
            route_id=str(route_id),
            reason=reason,
            affected_stop_count=affected,
        )
        return route

    async def mark_stop_arrived(self, tenant_id: UUID, user_id: UUID, stop_id: UUID) -> RouteStop:
        stop = await self._stop_repo.get_by_id(stop_id, tenant_id)
        if stop is None:
            raise RouteNotFoundError(f"RouteStop {stop_id} not found")
        if not can_stop_transition(RouteStopStatus(stop.status), RouteStopStatus.ARRIVED):
            raise InvalidRouteTransitionError(stop.status, RouteStopStatus.ARRIVED)
        return await self._stop_repo.update_status(
            stop_id, tenant_id, RouteStopStatus.ARRIVED, arrived_at=datetime.now(UTC)
        )

    async def mark_stop_complete(self, tenant_id: UUID, user_id: UUID, stop_id: UUID) -> RouteStop:
        stop = await self._stop_repo.get_by_id(stop_id, tenant_id)
        if stop is None:
            raise RouteNotFoundError(f"RouteStop {stop_id} not found")
        if not can_stop_transition(RouteStopStatus(stop.status), RouteStopStatus.COMPLETE):
            raise InvalidRouteTransitionError(stop.status, RouteStopStatus.COMPLETE)
        stop = await self._stop_repo.update_status(
            stop_id, tenant_id, RouteStopStatus.COMPLETE, completed_at=datetime.now(UTC)
        )
        await self._maybe_finalise_route(tenant_id, stop.route_id)
        return stop

    async def mark_stop_skipped(
        self, tenant_id: UUID, user_id: UUID, stop_id: UUID, reason: str = ""
    ) -> RouteStop:
        stop = await self._stop_repo.get_by_id(stop_id, tenant_id)
        if stop is None:
            raise RouteNotFoundError(f"RouteStop {stop_id} not found")
        if not can_stop_transition(RouteStopStatus(stop.status), RouteStopStatus.SKIPPED):
            raise InvalidRouteTransitionError(stop.status, RouteStopStatus.SKIPPED)
        stop = await self._stop_repo.update_status(stop_id, tenant_id, RouteStopStatus.SKIPPED)
        await self._maybe_finalise_route(tenant_id, stop.route_id)
        return stop

    async def resequence_route(
        self, tenant_id: UUID, user_id: UUID, route_id: UUID, *, job_ids: list[UUID]
    ) -> Route:
        """Reorder the stops of a committed route — the manual override.

        ``job_ids`` must be a permutation of the route's current stop jobs.
        Only ``committed`` routes can be resequenced (day-of reordering of an
        in-progress route is Slice 16 dynamic re-routing territory).
        Per-stop planned metrics travel with their job; they are estimates
        keyed to the old order, so totals are left unchanged.
        """
        route = await self._route_repo.get_by_id(route_id, tenant_id)
        if route is None:
            raise RouteNotFoundError(f"Route {route_id} not found")
        if RouteStatus(route.status) != RouteStatus.COMMITTED:
            raise InvalidRouteTransitionError(route.status, "resequenced")

        stops = await self._stop_repo.get_for_route(tenant_id, route_id)
        current_ids = {s.job_id for s in stops}
        requested_ids = set(job_ids)
        errors: list[str] = []
        if len(job_ids) != len(requested_ids):
            errors.append("job_ids contains duplicates")
        if requested_ids != current_ids:
            missing = current_ids - requested_ids
            unknown = requested_ids - current_ids
            if missing:
                errors.append(f"missing jobs: {sorted(str(j) for j in missing)}")
            if unknown:
                errors.append(f"unknown jobs: {sorted(str(j) for j in unknown)}")
        if errors:
            raise ManualSequenceInvalidError(
                "Resequence must be a permutation of the route's stops", errors=errors
            )

        by_job = {s.job_id: s for s in stops}
        stop_rows = [
            StopRow(
                job_id=jid,
                sequence_index=i,
                planned_eta=by_job[jid].planned_eta,
                planned_distance_from_prev_m=by_job[jid].planned_distance_from_prev_m,
                planned_duration_from_prev_s=by_job[jid].planned_duration_from_prev_s,
            )
            for i, jid in enumerate(job_ids)
        ]
        new_stops = await self._stop_repo.replace_all(tenant_id, route_id, stop_rows)
        route.stops = new_stops

        if self._audit is not None:
            await self._audit.log_event(
                event_type="route.resequenced",
                details={
                    "route_id": str(route_id),
                    "sequence": [str(j) for j in job_ids],
                },
                tenant_id=tenant_id,
                user_id=user_id,
            )
        log.info(
            "route.resequenced",
            route_id=str(route_id),
            stop_count=len(job_ids),
            tenant_id=str(tenant_id),
        )
        return route

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    async def get_route(self, tenant_id: UUID, route_id: UUID) -> Route:
        route = await self._route_repo.get_by_id(route_id, tenant_id)
        if route is None:
            raise RouteNotFoundError(f"Route {route_id} not found")
        return route

    async def list_routes(
        self,
        tenant_id: UUID,
        work_date,
        *,
        vehicle_id: UUID | None = None,
        status: list[str] | None = None,
    ) -> list[Route]:
        return await self._route_repo.list_for_date(
            tenant_id, work_date, vehicle_id=vehicle_id, status=status
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _resolve_option_mode(
        self, tenant_id: UUID, job_id: UUID, payload: DispatchCommitPayload
    ) -> tuple[UUID, list[StopRow]]:
        """Re-fetch routing options and return (vehicle_id, stop_rows)."""
        options = await self._schedule_svc.get_options(
            tenant_id,
            job_id,
            window_start=datetime.combine(payload.date, datetime.min.time()).replace(tzinfo=UTC),
            window_end=datetime.combine(payload.date, datetime.max.time()).replace(tzinfo=UTC),
        )
        if not options:
            raise RouteCommitConflictError(
                "No routing options available for this job/date", reason="no_options"
            )
        kind_map = {"nearest": 0, "earliest": 1, "balanced": 2}
        idx = kind_map.get(payload.option_kind or "nearest", 0)
        idx = min(idx, len(options) - 1)
        chosen = options[idx]
        stop_rows = [
            StopRow(
                job_id=job_id,
                sequence_index=0,
                planned_distance_from_prev_m=chosen.distance_meters,
                planned_duration_from_prev_s=chosen.travel_seconds,
            )
        ]
        return chosen.vehicle_id, stop_rows

    async def _resolve_manual_mode(
        self, tenant_id: UUID, job_id: UUID, payload: DispatchCommitPayload
    ) -> tuple[UUID, list[StopRow]]:
        """Validate and return (vehicle_id, stop_rows) for manual sequence."""
        vehicle_id = payload.manual_vehicle_id
        sequence = payload.manual_sequence or []

        errors: list[str] = []

        # Target job must appear exactly once
        if job_id not in sequence:
            errors.append(f"target job {job_id} must be present in manual_sequence")

        # No duplicates
        if len(sequence) != len(set(sequence)):
            errors.append("manual_sequence contains duplicate job IDs")

        if errors:
            raise ManualSequenceInvalidError("Manual sequence failed validation", errors=errors)

        # Validate each job exists and is not terminal
        for jid in sequence:
            job = await self._job_repo.get_by_id(jid, tenant_id)
            if job is None:
                errors.append(f"job {jid} not found in tenant")
            elif job.status in (JobStatus.COMPLETE, JobStatus.CANCELLED):
                errors.append(f"job {jid} is {job.status} and cannot be dispatched")

        if errors:
            raise ManualSequenceInvalidError("Manual sequence contains invalid jobs", errors=errors)

        stop_rows = [StopRow(job_id=jid, sequence_index=i) for i, jid in enumerate(sequence)]
        return vehicle_id, stop_rows

    async def _maybe_finalise_route(self, tenant_id: UUID, route_id: UUID) -> None:
        stops = await self._stop_repo.get_for_route(tenant_id, route_id)
        if stops and all(is_terminal_stop(RouteStopStatus(s.status)) for s in stops):
            await self._route_repo.update_status(
                route_id,
                tenant_id,
                RouteStatus.COMPLETE,
                completed_at=datetime.now(UTC),
            )
            log.info("route.auto_completed", route_id=str(route_id))


def make_in_memory_dispatch_service(
    schedule_service=None,
    job_repo=None,
    vehicle_repo=None,
    crew_repo=None,
) -> DispatchService:
    """Convenience factory for tests."""
    return DispatchService(
        route_repo=InMemoryRouteRepository(),
        stop_repo=InMemoryRouteStopRepository(),
        job_repo=job_repo,
        vehicle_repo=vehicle_repo,
        vehicle_crew_repo=crew_repo,
        schedule_service=schedule_service,
    )
