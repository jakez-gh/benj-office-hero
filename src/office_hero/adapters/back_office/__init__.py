"""Back-office adapter seam (ADR 056, Slice 24).

``BackOfficeAdapter`` is the protocol every external-system integration
implements; :class:`NativeAdapter` is the default binding where Office Hero
itself is the system of record.  Concrete CRM adapters (ServiceTitan,
PestPac, Jobber — slices 25-27) register in
:mod:`office_hero.adapters.back_office.registry`.

Delivery is at-least-once (the outbox re-delivers after a crash between
dispatch and mark_done), so every adapter method MUST be idempotent — the
outbox event's ``idem_key`` is available in each payload for deduplication
against the external API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable
from uuid import UUID


@dataclass
class Customer:
    id: UUID
    name: str
    # add more fields as needed in future


@dataclass
class Job:
    id: UUID
    customer_id: UUID
    # additional job-specific fields can go here


@runtime_checkable
class BackOfficeAdapter(Protocol):
    """Protocol that defines how the service interacts with a back-office system.

    All implementations must be asynchronous; the repository layer will handle
    conversion to/from the database or external API. Unit tests should depend on
    this protocol rather than concrete adapters.
    """

    async def health_check(self) -> bool: ...

    # Customer operations
    async def get_customer(self, id: UUID) -> Customer | None: ...

    async def create_customer(self, customer: Customer) -> Customer: ...

    async def update_customer(self, customer: Customer) -> Customer: ...

    async def delete_customer(self, id: UUID) -> None: ...

    # Job operations
    async def get_job(self, id: UUID) -> Job | None: ...

    async def create_job(self, job: Job) -> Job: ...

    async def update_job(self, job: Job) -> Job: ...

    async def delete_job(self, id: UUID) -> None: ...


class NativeAdapter:
    """Default back-office adapter: Office Hero is the system of record.

    Reads delegate to the local repositories (tenant-scoped, defence-in-depth
    per ADR 053).  Writes are acknowledgement no-ops: the domain services
    already persisted the row before the outbox event fired, so "syncing to
    the back office" is, natively, already done.  This keeps the seam's
    calling convention identical to the external adapters in slices 25-27.
    """

    name = "native"

    def __init__(self, tenant_id: UUID, customer_repo: Any, job_repo: Any) -> None:
        self._tenant_id = tenant_id
        self._customer_repo = customer_repo
        self._job_repo = job_repo

    async def health_check(self) -> bool:
        """Local DB is reachable whenever the app is — always healthy."""
        return True

    # -- Customer operations -------------------------------------------------

    async def get_customer(self, id: UUID) -> Customer | None:
        row = await self._customer_repo.get_by_id(id, self._tenant_id)
        if row is None:
            return None
        return Customer(id=row.id, name=row.name)

    async def create_customer(self, customer: Customer) -> Customer:
        # Row already exists locally (transactional outbox fires after the
        # domain write) — acknowledge idempotently.
        return customer

    async def update_customer(self, customer: Customer) -> Customer:
        return customer

    async def delete_customer(self, id: UUID) -> None:
        return None

    # -- Job operations -------------------------------------------------------

    async def get_job(self, id: UUID) -> Job | None:
        row = await self._job_repo.get_by_id(id, self._tenant_id)
        if row is None:
            return None
        return Job(id=row.id, customer_id=row.customer_id)

    async def create_job(self, job: Job) -> Job:
        return job

    async def update_job(self, job: Job) -> Job:
        return job

    async def delete_job(self, id: UUID) -> None:
        return None
