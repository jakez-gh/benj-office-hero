"""JobService — orchestrates Job CRUD, status lifecycle, and audit events.

All status mutations must go through :meth:`JobService._transition` which
delegates to :func:`~office_hero.core.job_status.can_transition`.  Direct
assignment ``job.status = ...`` anywhere outside this class is a bug.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from office_hero.core.exceptions import (
    CustomerNotFoundError,
    InvalidJobTransitionError,
    JobNotFoundError,
    LocationNotFoundError,
)
from office_hero.core.job_status import JobStatus, can_transition
from office_hero.core.logging import get_logger
from office_hero.models.job import Job
from office_hero.repositories.job_repository import JobRepositoryProtocol

log = get_logger(__name__)

_COMPLETION_NOTES_MAX_AUDIT = 1024
_IMMUTABLE_FIELDS = frozenset(
    {"status", "tenant_id", "customer_id", "industry", "created_by_user_id"}
)


class AuditPublisher(Protocol):
    """Minimal audit-publisher contract the service depends on (ADR 063)."""

    async def log_event(
        self,
        event_type: str,
        details: dict,
        tenant_id: UUID,
        user_id: UUID | None = None,
        request_id: UUID | None = None,
    ) -> None: ...


class JobService:
    """Business orchestration for the :class:`~office_hero.models.job.Job` aggregate."""

    def __init__(
        self,
        repo: JobRepositoryProtocol,
        customer_repo: Any,
        location_repo: Any,
        audit: AuditPublisher,
        template_registry: Any,
    ) -> None:
        """Inject the repository, cross-aggregate repos, audit publisher, and template registry."""
        self.repo = repo
        self.customer_repo = customer_repo
        self.location_repo = location_repo
        self.audit = audit
        self.template_registry = template_registry

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _transition(self, job: Job, target: JobStatus) -> None:
        """Validate and enforce the status-machine transition.

        Raises :class:`~office_hero.core.exceptions.InvalidJobTransitionError`
        when the transition is not in the allow-list.
        """
        current = JobStatus(job.status)
        if not can_transition(current, target):
            raise InvalidJobTransitionError(from_status=current, to_status=target)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(
        self,
        tenant_id: UUID,
        user_id: UUID,
        *,
        customer_id: UUID,
        location_id: UUID,
        title: str,
        description: str | None = None,
        priority: int = 50,
        service_type: str | None = None,
        requested_at: datetime | None = None,
        requested_until: datetime | None = None,
        estimated_duration_min: int = 60,
        custom_fields: dict | None = None,
        industry: str | None = None,
    ) -> Job:
        """Create a job with validation; emit ``job.created`` audit event."""
        # Verify customer belongs to this tenant (defence-in-depth).
        customer = await self.customer_repo.get_by_id(customer_id, tenant_id)
        if customer is None:
            raise CustomerNotFoundError(f"Customer {customer_id} not found in tenant {tenant_id}")

        # Verify location belongs to the same customer.
        location = await self.location_repo.get_by_id(location_id, tenant_id)
        if location is None:
            raise LocationNotFoundError(f"Location {location_id} not found in tenant {tenant_id}")
        if location.customer_id != customer_id:
            raise LocationNotFoundError(
                f"Location {location_id} does not belong to customer {customer_id}"
            )

        # Resolve industry: prefer explicit arg, fall back to what the caller supplies
        # (normally the Tenant's industry, resolved in the API layer).
        resolved_industry = industry or "generic"

        # Validate custom_fields against the industry template.
        cf = custom_fields or {}
        from office_hero.core.industry import Industry

        try:
            industry_enum = Industry(resolved_industry)
        except ValueError:
            industry_enum = Industry.GENERIC

        template = self.template_registry.get_template(industry_enum)
        cf = template.validate(cf)

        job = await self.repo.create(
            tenant_id,
            customer_id=customer_id,
            location_id=location_id,
            industry=resolved_industry,
            title=title,
            description=description,
            priority=priority,
            service_type=service_type,
            requested_at=requested_at,
            requested_until=requested_until,
            estimated_duration_min=estimated_duration_min,
            custom_fields=cf,
            created_by_user_id=user_id,
        )

        await self.audit.log_event(
            event_type="job.created",
            details={
                "job_id": str(job.id),
                "customer_id": str(customer_id),
                "location_id": str(location_id),
                "industry": resolved_industry,
                "priority": priority,
                "title": title,
            },
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return job

    async def get(self, tenant_id: UUID, job_id: UUID) -> Job:
        """Fetch a job or raise :class:`~office_hero.core.exceptions.JobNotFoundError`."""
        job = await self.repo.get_by_id(job_id, tenant_id)
        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found")
        return job

    async def list(
        self,
        tenant_id: UUID,
        *,
        status: list[str] | None = None,
        customer_id: UUID | None = None,
        scheduled_for_date: Any = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Job], int]:
        """Return ``(rows, total)`` for a tenant with optional filters."""
        return await self.repo.list(
            tenant_id,
            status=status,
            customer_id=customer_id,
            scheduled_for_date=scheduled_for_date,
            search=search,
            limit=limit,
            offset=offset,
        )

    async def update(
        self,
        tenant_id: UUID,
        user_id: UUID,
        job_id: UUID,
        patch: dict[str, Any],
    ) -> Job:
        """Apply a partial update; emits ``job.updated``.

        Immutable fields (status, tenant_id, customer_id, industry,
        created_by_user_id) cannot be patched here — callers should use
        the dedicated transition endpoints for status changes.
        """
        # Reject any attempt to patch immutable fields.
        forbidden = set(patch.keys()) & _IMMUTABLE_FIELDS
        if forbidden:
            raise ValueError(f"Fields {sorted(forbidden)} cannot be updated via patch")

        existing = await self.get(tenant_id, job_id)

        # If location_id is changing, verify the new location still belongs to the same customer.
        if "location_id" in patch and patch["location_id"] != existing.location_id:
            new_loc = await self.location_repo.get_by_id(patch["location_id"], tenant_id)
            if new_loc is None:
                raise LocationNotFoundError(
                    f"Location {patch['location_id']} not found in tenant {tenant_id}"
                )
            if new_loc.customer_id != existing.customer_id:
                raise LocationNotFoundError(
                    f"Location {patch['location_id']} does not belong to customer {existing.customer_id}"
                )

        # Re-validate custom_fields if they're being updated.
        if "custom_fields" in patch:
            from office_hero.core.industry import Industry

            try:
                industry_enum = Industry(existing.industry)
            except ValueError:
                industry_enum = Industry.GENERIC
            template = self.template_registry.get_template(industry_enum)
            patch["custom_fields"] = template.validate(patch["custom_fields"])

        # Build diff for audit.
        before: dict[str, Any] = {}
        after: dict[str, Any] = {}
        for key, value in patch.items():
            current = getattr(existing, key, None)
            if current != value:
                before[key] = str(current) if isinstance(current, UUID) else current
                after[key] = str(value) if isinstance(value, UUID) else value

        updated = await self.repo.update_fields(job_id, tenant_id, **patch)
        await self.audit.log_event(
            event_type="job.updated",
            details={"job_id": str(job_id), "before": before, "after": after},
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return updated

    # ------------------------------------------------------------------
    # Status lifecycle transitions
    # ------------------------------------------------------------------

    async def schedule(
        self, tenant_id: UUID, user_id: UUID, job_id: UUID, scheduled_for: datetime
    ) -> Job:
        """Transition ``pending → scheduled``; emit ``job.scheduled``."""
        job = await self.get(tenant_id, job_id)
        self._transition(job, JobStatus.SCHEDULED)
        job = await self.repo.update_status(
            job_id,
            tenant_id,
            JobStatus.SCHEDULED,
            scheduled_for=scheduled_for,
        )
        await self.audit.log_event(
            event_type="job.scheduled",
            details={
                "job_id": str(job_id),
                "from": "pending",
                "to": "scheduled",
                "scheduled_for": scheduled_for.isoformat(),
            },
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return job

    async def start(self, tenant_id: UUID, user_id: UUID, job_id: UUID) -> Job:
        """Transition ``scheduled → in_progress``; emit ``job.started``."""
        job = await self.get(tenant_id, job_id)
        self._transition(job, JobStatus.IN_PROGRESS)
        now = datetime.now(UTC)
        job = await self.repo.update_status(
            job_id,
            tenant_id,
            JobStatus.IN_PROGRESS,
            started_at=now,
        )
        await self.audit.log_event(
            event_type="job.started",
            details={
                "job_id": str(job_id),
                "from": "scheduled",
                "to": "in_progress",
                "started_at": now.isoformat(),
            },
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return job

    async def complete(
        self,
        tenant_id: UUID,
        user_id: UUID,
        job_id: UUID,
        *,
        completion_notes: str | None = None,
    ) -> Job:
        """Transition ``in_progress → complete``; emit ``job.completed``."""
        job = await self.get(tenant_id, job_id)
        self._transition(job, JobStatus.COMPLETE)
        now = datetime.now(UTC)
        job = await self.repo.update_status(
            job_id,
            tenant_id,
            JobStatus.COMPLETE,
            completed_at=now,
        )
        truncated_notes = (
            completion_notes[:_COMPLETION_NOTES_MAX_AUDIT]
            if completion_notes and len(completion_notes) > _COMPLETION_NOTES_MAX_AUDIT
            else completion_notes
        )
        await self.audit.log_event(
            event_type="job.completed",
            details={
                "job_id": str(job_id),
                "from": "in_progress",
                "to": "complete",
                "completed_at": now.isoformat(),
                "completion_notes": truncated_notes,
            },
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return job

    async def cancel(self, tenant_id: UUID, user_id: UUID, job_id: UUID, *, reason: str) -> Job:
        """Transition any non-terminal status → ``cancelled``; emit ``job.cancelled``.

        ``reason`` is required (min length 3).
        """
        if len(reason.strip()) < 3:
            raise ValueError("cancel reason must be at least 3 characters")

        job = await self.get(tenant_id, job_id)
        from_status = job.status
        self._transition(job, JobStatus.CANCELLED)
        now = datetime.now(UTC)
        job = await self.repo.update_status(
            job_id,
            tenant_id,
            JobStatus.CANCELLED,
            cancelled_at=now,
            cancel_reason=reason,
        )
        await self.audit.log_event(
            event_type="job.cancelled",
            details={
                "job_id": str(job_id),
                "from_status": from_status,
                "to": "cancelled",
                "reason": reason,
                "cancelled_at": now.isoformat(),
            },
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return job
