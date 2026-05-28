"""Job dispatch service — assign a vehicle and book a scheduled time slot.

The single public method ``dispatch`` handles the full atomic transition:
  pending → scheduled, with vehicle assignment and conflict detection.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from office_hero.core.exceptions import (
    InvalidJobTransitionError,
    JobNotFoundError,
    VehicleAlreadyBookedError,
    VehicleNotFoundError,
)
from office_hero.core.job_status import JobStatus, can_transition
from office_hero.core.logging import get_logger
from office_hero.models.job import Job
from office_hero.repositories.job_repository import JobRepositoryProtocol
from office_hero.repositories.vehicle_repository import VehicleRepositoryProtocol

log = get_logger(__name__)


class JobDispatchService:
    """Orchestrates the scheduling / dispatch of a job to a vehicle."""

    def __init__(
        self,
        job_repo: JobRepositoryProtocol,
        vehicle_repo: VehicleRepositoryProtocol,
    ) -> None:
        self._job_repo = job_repo
        self._vehicle_repo = vehicle_repo

    async def dispatch(
        self,
        tenant_id: UUID,
        job_id: UUID,
        *,
        vehicle_id: UUID,
        scheduled_for: datetime,
    ) -> Job:
        """Assign *vehicle_id* to *job_id* and schedule it for *scheduled_for*.

        Raises:
            JobNotFoundError: job doesn't exist in this tenant.
            VehicleNotFoundError: vehicle doesn't exist in this tenant.
            InvalidJobTransitionError: job is not in a dispatchable state.
            VehicleAlreadyBookedError: vehicle has an overlapping scheduled job.
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

        updated = await self._job_repo.update_fields(
            job_id,
            tenant_id,
            status=JobStatus.SCHEDULED.value,
            assigned_vehicle_id=vehicle_id,
            scheduled_for=scheduled_for,
        )
        if updated is None:
            raise JobNotFoundError(f"Job {job_id} disappeared during dispatch")
        log.info(
            "job.dispatched",
            job_id=str(job_id),
            vehicle_id=str(vehicle_id),
            scheduled_for=scheduled_for.isoformat(),
            tenant_id=str(tenant_id),
        )
        return updated
