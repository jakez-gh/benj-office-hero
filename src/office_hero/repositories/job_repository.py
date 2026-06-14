"""Job repository — protocol, SQLAlchemy impl, and in-memory mock.

The protocol is what the service layer depends on (ADR 058).  The concrete
SQLAlchemy implementation is the production binding.  The in-memory mock is
used by unit tests so the service layer can be exercised without a database.
All implementations enforce tenant scoping defensively (ADR 053
defence-in-depth on top of RLS).
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, date, datetime
from typing import Any, Protocol, runtime_checkable
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from office_hero.core.exceptions import JobNotFoundError
from office_hero.models.job import Job


@runtime_checkable
class JobRepositoryProtocol(Protocol):
    """Repository contract for :class:`Job` persistence."""

    async def create(
        self,
        tenant_id: UUID,
        *,
        customer_id: UUID,
        location_id: UUID,
        industry: str,
        title: str,
        description: str | None,
        priority: int,
        service_type: str | None,
        requested_at: datetime | None,
        requested_until: datetime | None,
        estimated_duration_min: int,
        custom_fields: dict,
        created_by_user_id: UUID,
        contract_id: UUID | None = None,
    ) -> Job: ...

    async def get_by_id(self, job_id: UUID, tenant_id: UUID) -> Job | None: ...

    async def bulk_get_by_ids(self, job_ids: list[UUID], tenant_id: UUID) -> list[Job]: ...

    async def list(
        self,
        tenant_id: UUID,
        *,
        status: list[str] | None = None,
        customer_id: UUID | None = None,
        assigned_vehicle_id: UUID | None = None,
        scheduled_for_date: date | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Job], int]: ...

    async def update_fields(self, job_id: UUID, tenant_id: UUID, **patch: Any) -> Job: ...

    async def update_status(
        self,
        job_id: UUID,
        tenant_id: UUID,
        new_status: str,
        *,
        scheduled_for: datetime | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        cancelled_at: datetime | None = None,
        cancel_reason: str | None = None,
    ) -> Job: ...

    async def list_due_for_routing(self, tenant_id: UUID, for_date: date) -> list[Job]: ...

    async def list_by_vehicle_in_window(
        self,
        tenant_id: UUID,
        vehicle_id: UUID,
        window_start: datetime,
        window_end: datetime,
    ) -> list[Job]: ...


class JobRepository:
    """SQLAlchemy-backed concrete :class:`Job` repository (ADR 058)."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind to an async SQLAlchemy session."""
        self.session = session

    async def create(
        self,
        tenant_id: UUID,
        *,
        customer_id: UUID,
        location_id: UUID,
        industry: str,
        title: str,
        description: str | None = None,
        priority: int = 50,
        service_type: str | None = None,
        requested_at: datetime | None = None,
        requested_until: datetime | None = None,
        estimated_duration_min: int = 60,
        custom_fields: dict | None = None,
        created_by_user_id: UUID,
        contract_id: UUID | None = None,
    ) -> Job:
        """Insert and flush a new :class:`Job`."""
        job = Job(
            tenant_id=tenant_id,
            customer_id=customer_id,
            location_id=location_id,
            industry=industry,
            title=title,
            description=description,
            status="pending",
            priority=priority,
            service_type=service_type,
            requested_at=requested_at,
            requested_until=requested_until,
            estimated_duration_min=estimated_duration_min,
            custom_fields=custom_fields or {},
            created_by_user_id=created_by_user_id,
            contract_id=contract_id,
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def get_by_id(self, job_id: UUID, tenant_id: UUID) -> Job | None:
        """Fetch a job if it exists in ``tenant_id`` (defence-in-depth)."""
        stmt = select(Job).where(Job.id == job_id, Job.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def bulk_get_by_ids(self, job_ids: list[UUID], tenant_id: UUID) -> list[Job]:
        """Fetch many jobs by id within ``tenant_id`` in a single query."""
        if not job_ids:
            return []
        stmt = select(Job).where(Job.id.in_(job_ids), Job.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list(
        self,
        tenant_id: UUID,
        *,
        status: list[str] | None = None,
        customer_id: UUID | None = None,
        assigned_vehicle_id: UUID | None = None,
        scheduled_for_date: date | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Job], int]:
        """Return ``(rows, total)`` for a tenant with optional filters."""
        where_clauses = [Job.tenant_id == tenant_id]

        if status:
            where_clauses.append(Job.status.in_(status))
        if customer_id is not None:
            where_clauses.append(Job.customer_id == customer_id)
        if assigned_vehicle_id is not None:
            where_clauses.append(Job.assigned_vehicle_id == assigned_vehicle_id)
        if scheduled_for_date is not None:
            # Cast the timestamptz to date for comparison.
            where_clauses.append(func.date(Job.scheduled_for) == scheduled_for_date)
        if search:
            pattern = f"%{search}%"
            where_clauses.append(or_(Job.title.ilike(pattern), Job.description.ilike(pattern)))

        count_stmt = select(func.count(Job.id)).where(and_(*where_clauses))
        total = int((await self.session.execute(count_stmt)).scalar_one())

        rows_stmt = (
            select(Job)
            .where(and_(*where_clauses))
            .order_by(Job.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = list((await self.session.execute(rows_stmt)).scalars().all())
        return rows, total

    async def update_fields(self, job_id: UUID, tenant_id: UUID, **patch: Any) -> Job:
        """Apply a partial update to non-status fields; raises if absent."""
        job = await self.get_by_id(job_id, tenant_id)
        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found")
        for key, value in patch.items():
            setattr(job, key, value)
        await self.session.flush()
        return job

    async def update_status(
        self,
        job_id: UUID,
        tenant_id: UUID,
        new_status: str,
        *,
        scheduled_for: datetime | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        cancelled_at: datetime | None = None,
        cancel_reason: str | None = None,
    ) -> Job:
        """Set status + the matching lifecycle timestamp atomically."""
        job = await self.get_by_id(job_id, tenant_id)
        if job is None:
            raise JobNotFoundError(f"Job {job_id} not found")
        job.status = new_status
        if scheduled_for is not None:
            job.scheduled_for = scheduled_for
        if started_at is not None:
            job.started_at = started_at
        if completed_at is not None:
            job.completed_at = completed_at
        if cancelled_at is not None:
            job.cancelled_at = cancelled_at
        if cancel_reason is not None:
            job.cancel_reason = cancel_reason
        await self.session.flush()
        return job

    async def list_due_for_routing(self, tenant_id: UUID, for_date: date) -> list[Job]:
        """Return pending/scheduled jobs for the given date (for Slice-13 routing)."""
        stmt = (
            select(Job)
            .where(
                Job.tenant_id == tenant_id,
                Job.status.in_(["pending", "scheduled"]),
                or_(
                    func.date(Job.scheduled_for) == for_date,
                    func.date(Job.requested_at) == for_date,
                ),
            )
            .order_by(Job.priority.asc(), Job.scheduled_for.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_vehicle_in_window(
        self,
        tenant_id: UUID,
        vehicle_id: UUID,
        window_start: datetime,
        window_end: datetime,
    ) -> list[Job]:
        """Return scheduled/in_progress jobs for a vehicle that overlap the window."""
        stmt = select(Job).where(
            Job.tenant_id == tenant_id,
            Job.assigned_vehicle_id == vehicle_id,
            Job.status.in_(["scheduled", "in_progress"]),
            Job.scheduled_for < window_end,
            Job.scheduled_for + func.make_interval(0, 0, 0, 0, 0, Job.estimated_duration_min)
            > window_start,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class InMemoryJobRepository:
    """In-memory mock implementing :class:`JobRepositoryProtocol`.

    Used by unit tests so the service layer can be exercised without a DB.
    Tenant scope is honoured on every read/write so tests can assert the
    cross-tenant behaviour of the service layer.
    """

    def __init__(self) -> None:
        self._rows: dict[UUID, dict[str, Any]] = {}

    def _row_to_job(self, row: dict[str, Any]) -> Job:
        job = Job(
            id=row["id"],
            tenant_id=row["tenant_id"],
            customer_id=row["customer_id"],
            location_id=row["location_id"],
            industry=row["industry"],
            title=row["title"],
            description=row.get("description"),
            status=row["status"],
            priority=row["priority"],
            service_type=row.get("service_type"),
            requested_at=row.get("requested_at"),
            requested_until=row.get("requested_until"),
            estimated_duration_min=row["estimated_duration_min"],
            scheduled_for=row.get("scheduled_for"),
            started_at=row.get("started_at"),
            completed_at=row.get("completed_at"),
            cancelled_at=row.get("cancelled_at"),
            cancel_reason=row.get("cancel_reason"),
            custom_fields=deepcopy(row.get("custom_fields", {})),
            external_id=row.get("external_id"),
            contract_id=row.get("contract_id"),
            assigned_vehicle_id=row.get("assigned_vehicle_id"),
            created_by_user_id=row["created_by_user_id"],
        )
        job.created_at = row["created_at"]
        job.updated_at = row["updated_at"]
        return job

    async def create(
        self,
        tenant_id: UUID,
        *,
        customer_id: UUID,
        location_id: UUID,
        industry: str,
        title: str,
        description: str | None = None,
        priority: int = 50,
        service_type: str | None = None,
        requested_at: datetime | None = None,
        requested_until: datetime | None = None,
        estimated_duration_min: int = 60,
        custom_fields: dict | None = None,
        created_by_user_id: UUID,
        contract_id: UUID | None = None,
    ) -> Job:
        """Insert and return a freshly minted :class:`Job`."""
        jid = uuid4()
        now = datetime.now(UTC)
        self._rows[jid] = {
            "id": jid,
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "location_id": location_id,
            "industry": industry,
            "title": title,
            "description": description,
            "status": "pending",
            "priority": priority,
            "service_type": service_type,
            "requested_at": requested_at,
            "requested_until": requested_until,
            "estimated_duration_min": estimated_duration_min,
            "scheduled_for": None,
            "started_at": None,
            "completed_at": None,
            "cancelled_at": None,
            "cancel_reason": None,
            "custom_fields": deepcopy(custom_fields or {}),
            "external_id": None,
            "contract_id": contract_id,
            "assigned_vehicle_id": None,
            "created_by_user_id": created_by_user_id,
            "created_at": now,
            "updated_at": now,
        }
        return self._row_to_job(self._rows[jid])

    async def get_by_id(self, job_id: UUID, tenant_id: UUID) -> Job | None:
        """Return the job if it exists in this tenant's scope."""
        row = self._rows.get(job_id)
        if row is None or row["tenant_id"] != tenant_id:
            return None
        return self._row_to_job(row)

    async def bulk_get_by_ids(self, job_ids: list[UUID], tenant_id: UUID) -> list[Job]:
        """Return all jobs in this tenant whose id is in ``job_ids``."""
        wanted = set(job_ids)
        return [
            self._row_to_job(r)
            for r in self._rows.values()
            if r["tenant_id"] == tenant_id and r["id"] in wanted
        ]

    async def list(
        self,
        tenant_id: UUID,
        *,
        status: list[str] | None = None,
        customer_id: UUID | None = None,
        assigned_vehicle_id: UUID | None = None,
        scheduled_for_date: date | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Job], int]:
        """Return ``(rows, total)`` matching the filter."""
        rows = [r for r in self._rows.values() if r["tenant_id"] == tenant_id]

        if status:
            rows = [r for r in rows if r["status"] in status]
        if customer_id is not None:
            rows = [r for r in rows if r["customer_id"] == customer_id]
        if assigned_vehicle_id is not None:
            rows = [r for r in rows if r.get("assigned_vehicle_id") == assigned_vehicle_id]
        if scheduled_for_date is not None:
            rows = [
                r
                for r in rows
                if r.get("scheduled_for") is not None
                and r["scheduled_for"].date() == scheduled_for_date
            ]
        if search:
            needle = search.lower()
            rows = [
                r
                for r in rows
                if needle in (r["title"] or "").lower()
                or needle in ((r.get("description") or "").lower())
            ]

        rows.sort(key=lambda r: r["created_at"], reverse=True)
        total = len(rows)
        page = rows[offset : offset + limit]
        return [self._row_to_job(r) for r in page], total

    async def update_fields(self, job_id: UUID, tenant_id: UUID, **patch: Any) -> Job:
        """Apply a partial update; raises if cross-tenant or absent."""
        row = self._rows.get(job_id)
        if row is None or row["tenant_id"] != tenant_id:
            raise JobNotFoundError(f"Job {job_id} not found")
        for key, value in deepcopy(patch).items():
            row[key] = value
        row["updated_at"] = datetime.now(UTC)
        return self._row_to_job(row)

    async def update_status(
        self,
        job_id: UUID,
        tenant_id: UUID,
        new_status: str,
        *,
        scheduled_for: datetime | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        cancelled_at: datetime | None = None,
        cancel_reason: str | None = None,
    ) -> Job:
        """Set status + lifecycle timestamp atomically."""
        row = self._rows.get(job_id)
        if row is None or row["tenant_id"] != tenant_id:
            raise JobNotFoundError(f"Job {job_id} not found")
        row["status"] = new_status
        if scheduled_for is not None:
            row["scheduled_for"] = scheduled_for
        if started_at is not None:
            row["started_at"] = started_at
        if completed_at is not None:
            row["completed_at"] = completed_at
        if cancelled_at is not None:
            row["cancelled_at"] = cancelled_at
        if cancel_reason is not None:
            row["cancel_reason"] = cancel_reason
        row["updated_at"] = datetime.now(UTC)
        return self._row_to_job(row)

    async def list_due_for_routing(self, tenant_id: UUID, for_date: date) -> list[Job]:
        """Return pending/scheduled jobs due on *for_date* (Slice-13 routing)."""
        rows = [
            r
            for r in self._rows.values()
            if r["tenant_id"] == tenant_id
            and r["status"] in ("pending", "scheduled")
            and (
                (r.get("scheduled_for") is not None and r["scheduled_for"].date() == for_date)
                or (r.get("requested_at") is not None and r["requested_at"].date() == for_date)
            )
        ]
        rows.sort(key=lambda r: (r["priority"], r.get("scheduled_for") or datetime.max))
        return [self._row_to_job(r) for r in rows]

    async def list_by_vehicle_in_window(
        self,
        tenant_id: UUID,
        vehicle_id: UUID,
        window_start: datetime,
        window_end: datetime,
    ) -> list[Job]:
        """Return scheduled/in_progress jobs for a vehicle that overlap the window."""
        from datetime import timedelta

        result = []
        for r in self._rows.values():
            if r["tenant_id"] != tenant_id:
                continue
            if r.get("assigned_vehicle_id") != vehicle_id:
                continue
            if r["status"] not in ("scheduled", "in_progress"):
                continue
            sf = r.get("scheduled_for")
            if sf is None:
                continue
            duration = timedelta(minutes=r.get("estimated_duration_min", 60))
            job_end = sf + duration
            if sf < window_end and job_end > window_start:
                result.append(self._row_to_job(r))
        return result
