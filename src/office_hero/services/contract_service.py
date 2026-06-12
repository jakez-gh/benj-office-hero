"""ContractService — recurring service agreements and due-job generation (Slice 11).

All status mutations must go through :meth:`ContractService._transition` which
delegates to :func:`~office_hero.core.contract_status.can_transition`.  Direct
assignment ``contract.status = ...`` anywhere outside this class is a bug.

Job generation is idempotent by construction: ``next_due`` advances in the same
unit of work as job creation, so re-running ``generate_due_jobs`` with the same
``as_of`` produces nothing new.  Concurrent generation runs are out of scope for
v1 (single app instance; trigger is manual or cron).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any, Protocol
from uuid import UUID

from office_hero.core.contract_frequency import ContractFrequency, advance_date
from office_hero.core.contract_status import ContractStatus, can_transition
from office_hero.core.exceptions import (
    ContractNotFoundError,
    CustomerNotFoundError,
    InvalidContractTransitionError,
    LocationNotFoundError,
)
from office_hero.core.logging import get_logger
from office_hero.models.contract import Contract
from office_hero.models.job import Job
from office_hero.repositories.contract_repository import ContractRepositoryProtocol
from office_hero.repositories.job_repository import JobRepositoryProtocol

log = get_logger(__name__)

# Runaway guard: a single generation run never creates more than this many
# jobs per contract (covers ~6 months of weekly catch-up).
_MAX_JOBS_PER_CONTRACT_PER_RUN = 24

# Generated jobs materialise at this UTC time on their due date. Tenant-local
# business hours need a tenant timezone column — flagged as future work in the
# slice design.
_GENERATED_JOB_HOUR_UTC = 9

_IMMUTABLE_FIELDS = frozenset(
    {"status", "tenant_id", "customer_id", "industry", "created_by_user_id", "frequency"}
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


class ContractService:
    """Business orchestration for the :class:`~office_hero.models.contract.Contract` aggregate."""

    def __init__(
        self,
        repo: ContractRepositoryProtocol,
        customer_repo: Any,
        location_repo: Any,
        job_repo: JobRepositoryProtocol,
        audit: AuditPublisher,
        template_registry: Any,
    ) -> None:
        """Inject the repository, cross-aggregate repos, audit publisher, and template registry."""
        self.repo = repo
        self.customer_repo = customer_repo
        self.location_repo = location_repo
        self.job_repo = job_repo
        self.audit = audit
        self.template_registry = template_registry

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _transition(self, contract: Contract, target: ContractStatus) -> None:
        """Validate and enforce the status-machine transition."""
        current = ContractStatus(contract.status)
        if not can_transition(current, target):
            raise InvalidContractTransitionError(from_status=current, to_status=target)

    def _validate_custom_fields(self, industry: str, custom_fields: dict) -> dict:
        """Validate ``custom_fields`` against the industry template registry."""
        from office_hero.core.industry import Industry

        try:
            industry_enum = Industry(industry)
        except ValueError:
            industry_enum = Industry.GENERIC
        template = self.template_registry.get_template(industry_enum)
        return template.validate(custom_fields)

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
        service_type: str | None = None,
        priority: int = 50,
        estimated_duration_min: int = 60,
        frequency: str,
        start_date: date,
        end_date: date | None = None,
        custom_fields: dict | None = None,
        industry: str | None = None,
    ) -> Contract:
        """Create a contract with validation; emit ``contract.created``."""
        customer = await self.customer_repo.get_by_id(customer_id, tenant_id)
        if customer is None:
            raise CustomerNotFoundError(f"Customer {customer_id} not found in tenant {tenant_id}")

        location = await self.location_repo.get_by_id(location_id, tenant_id)
        if location is None:
            raise LocationNotFoundError(f"Location {location_id} not found in tenant {tenant_id}")
        if location.customer_id != customer_id:
            raise LocationNotFoundError(
                f"Location {location_id} does not belong to customer {customer_id}"
            )

        ContractFrequency(frequency)  # raises ValueError on unknown cadence
        if end_date is not None and end_date < start_date:
            raise ValueError("end_date must be on or after start_date")

        resolved_industry = industry or "generic"
        cf = self._validate_custom_fields(resolved_industry, custom_fields or {})

        contract = await self.repo.create(
            tenant_id,
            customer_id=customer_id,
            location_id=location_id,
            industry=resolved_industry,
            title=title,
            description=description,
            service_type=service_type,
            priority=priority,
            estimated_duration_min=estimated_duration_min,
            frequency=frequency,
            start_date=start_date,
            next_due=start_date,
            end_date=end_date,
            custom_fields=cf,
            created_by_user_id=user_id,
        )

        await self.audit.log_event(
            event_type="contract.created",
            details={
                "contract_id": str(contract.id),
                "customer_id": str(customer_id),
                "location_id": str(location_id),
                "industry": resolved_industry,
                "frequency": frequency,
                "start_date": start_date.isoformat(),
                "title": title,
            },
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return contract

    async def get(self, tenant_id: UUID, contract_id: UUID) -> Contract:
        """Fetch a contract or raise :class:`ContractNotFoundError`."""
        contract = await self.repo.get_by_id(contract_id, tenant_id)
        if contract is None:
            raise ContractNotFoundError(f"Contract {contract_id} not found")
        return contract

    async def list(
        self,
        tenant_id: UUID,
        *,
        status: list[str] | None = None,
        customer_id: UUID | None = None,
        due_before: date | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Contract], int]:
        """Return ``(rows, total)`` for a tenant with optional filters."""
        return await self.repo.list(
            tenant_id,
            status=status,
            customer_id=customer_id,
            due_before=due_before,
            search=search,
            limit=limit,
            offset=offset,
        )

    async def update(
        self,
        tenant_id: UUID,
        user_id: UUID,
        contract_id: UUID,
        patch: dict[str, Any],
    ) -> Contract:
        """Apply a partial update; emits ``contract.updated``.

        Immutable fields (status, tenant_id, customer_id, industry, frequency,
        created_by_user_id) cannot be patched — status uses the dedicated
        pause/resume/end endpoints.  ``next_due`` IS patchable ("skip a visit"
        is a legitimate workflow).
        """
        forbidden = set(patch.keys()) & _IMMUTABLE_FIELDS
        if forbidden:
            raise ValueError(f"Fields {sorted(forbidden)} cannot be updated via patch")

        existing = await self.get(tenant_id, contract_id)

        if "location_id" in patch and patch["location_id"] != existing.location_id:
            new_loc = await self.location_repo.get_by_id(patch["location_id"], tenant_id)
            if new_loc is None:
                raise LocationNotFoundError(
                    f"Location {patch['location_id']} not found in tenant {tenant_id}"
                )
            if new_loc.customer_id != existing.customer_id:
                raise LocationNotFoundError(
                    f"Location {patch['location_id']} does not belong to "
                    f"customer {existing.customer_id}"
                )

        if "custom_fields" in patch:
            patch["custom_fields"] = self._validate_custom_fields(
                existing.industry, patch["custom_fields"]
            )

        end_date = patch.get("end_date", existing.end_date)
        start_date = patch.get("start_date", existing.start_date)
        if end_date is not None and end_date < start_date:
            raise ValueError("end_date must be on or after start_date")

        before: dict[str, Any] = {}
        after: dict[str, Any] = {}
        for key, value in patch.items():
            current = getattr(existing, key, None)
            if current != value:
                before[key] = str(current) if isinstance(current, UUID | date) else current
                after[key] = str(value) if isinstance(value, UUID | date) else value

        updated = await self.repo.update_fields(contract_id, tenant_id, **patch)
        await self.audit.log_event(
            event_type="contract.updated",
            details={"contract_id": str(contract_id), "before": before, "after": after},
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return updated

    # ------------------------------------------------------------------
    # Status lifecycle transitions
    # ------------------------------------------------------------------

    async def pause(self, tenant_id: UUID, user_id: UUID, contract_id: UUID) -> Contract:
        """Transition ``active → paused``; emit ``contract.paused``."""
        contract = await self.get(tenant_id, contract_id)
        self._transition(contract, ContractStatus.PAUSED)
        now = datetime.now(UTC)
        contract = await self.repo.update_status(
            contract_id, tenant_id, ContractStatus.PAUSED, paused_at=now
        )
        await self.audit.log_event(
            event_type="contract.paused",
            details={"contract_id": str(contract_id), "paused_at": now.isoformat()},
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return contract

    async def resume(self, tenant_id: UUID, user_id: UUID, contract_id: UUID) -> Contract:
        """Transition ``paused → active``; emit ``contract.resumed``.

        ``next_due`` dates that fell while paused are NOT back-filled: if
        ``next_due`` is in the past it is rolled forward to the first due date
        on/after today so resuming doesn't dump a backlog of stale visits.
        """
        contract = await self.get(tenant_id, contract_id)
        self._transition(contract, ContractStatus.ACTIVE)
        contract = await self.repo.update_status(contract_id, tenant_id, ContractStatus.ACTIVE)

        today = datetime.now(UTC).date()
        next_due = contract.next_due
        frequency = ContractFrequency(contract.frequency)
        rolled = False
        while next_due < today:
            next_due = advance_date(next_due, frequency)
            rolled = True
        if rolled:
            contract = await self.repo.update_fields(contract_id, tenant_id, next_due=next_due)

        await self.audit.log_event(
            event_type="contract.resumed",
            details={"contract_id": str(contract_id), "next_due": contract.next_due.isoformat()},
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return contract

    async def end(
        self, tenant_id: UUID, user_id: UUID, contract_id: UUID, *, reason: str | None = None
    ) -> Contract:
        """Transition any non-terminal status → ``ended``; emit ``contract.ended``."""
        contract = await self.get(tenant_id, contract_id)
        self._transition(contract, ContractStatus.ENDED)
        now = datetime.now(UTC)
        contract = await self.repo.update_status(
            contract_id,
            tenant_id,
            ContractStatus.ENDED,
            ended_at=now,
            end_reason=reason,
        )
        await self.audit.log_event(
            event_type="contract.ended",
            details={
                "contract_id": str(contract_id),
                "reason": reason,
                "ended_at": now.isoformat(),
            },
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return contract

    # ------------------------------------------------------------------
    # Job generation
    # ------------------------------------------------------------------

    async def generate_due_jobs(
        self,
        tenant_id: UUID,
        user_id: UUID,
        *,
        as_of: date | None = None,
    ) -> list[Job]:
        """Materialise Jobs for every active contract due on/before ``as_of``.

        Returns the list of created Jobs.  Emits one
        ``contract.jobs_generated`` audit event summarising the run.
        Contracts whose advanced ``next_due`` passes ``end_date`` are
        auto-ended.
        """
        run_date = as_of or datetime.now(UTC).date()
        created: list[Job] = []
        contract_ids: set[str] = set()

        for contract in await self.repo.list_due(tenant_id, run_date):
            frequency = ContractFrequency(contract.frequency)
            next_due = contract.next_due

            for _ in range(_MAX_JOBS_PER_CONTRACT_PER_RUN):
                if next_due > run_date:
                    break
                if contract.end_date is not None and next_due > contract.end_date:
                    break

                requested_at = datetime.combine(
                    next_due, time(hour=_GENERATED_JOB_HOUR_UTC), tzinfo=UTC
                )
                job = await self.job_repo.create(
                    tenant_id,
                    customer_id=contract.customer_id,
                    location_id=contract.location_id,
                    industry=contract.industry,
                    title=f"{contract.title} — {next_due.strftime('%b %d, %Y')}",
                    description=contract.description,
                    priority=contract.priority,
                    service_type=contract.service_type,
                    requested_at=requested_at,
                    requested_until=requested_at + timedelta(hours=8),
                    estimated_duration_min=contract.estimated_duration_min,
                    custom_fields=dict(contract.custom_fields),
                    created_by_user_id=user_id,
                    contract_id=contract.id,
                )
                created.append(job)
                contract_ids.add(str(contract.id))

                next_due = advance_date(next_due, frequency)
                # Advance in the same unit of work as job creation so a re-run
                # with the same as_of generates nothing (idempotency).
                await self.repo.update_fields(contract.id, tenant_id, next_due=next_due)

            if contract.end_date is not None and next_due > contract.end_date:
                # Recurrence ran off the end of the agreement — end it.
                self._transition(contract, ContractStatus.ENDED)
                now = datetime.now(UTC)
                await self.repo.update_status(
                    contract.id,
                    tenant_id,
                    ContractStatus.ENDED,
                    ended_at=now,
                    end_reason="end_date reached",
                )
                await self.audit.log_event(
                    event_type="contract.ended",
                    details={
                        "contract_id": str(contract.id),
                        "reason": "end_date reached",
                        "ended_at": now.isoformat(),
                    },
                    tenant_id=tenant_id,
                    user_id=user_id,
                )

        if created:
            await self.audit.log_event(
                event_type="contract.jobs_generated",
                details={
                    "as_of": run_date.isoformat(),
                    "contract_ids": sorted(contract_ids),
                    "job_ids": [str(j.id) for j in created],
                    "count": len(created),
                },
                tenant_id=tenant_id,
                user_id=user_id,
            )
            log.info(
                "contract.jobs_generated",
                tenant_id=str(tenant_id),
                count=len(created),
                as_of=run_date.isoformat(),
            )
        return created
