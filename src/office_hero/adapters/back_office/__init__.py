from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable
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
    """Default back-office adapter using Office Hero as the system of record.

    In the initial implementation the methods raise ``NotImplementedError``.
    Later slices will refactor service/repository code to provide a concrete
    implementation using the application's own database.
    """

    async def health_check(self) -> bool:
        # local DB should always be reachable when the application is running.
        # external adapters may override to perform network calls.
        return True

    # The following are stubs; real behaviour will be added when the
    # repository interfaces are available.  They exist primarily so the class
    # satisfies the ``BackOfficeAdapter`` protocol.

    async def get_customer(self, id: UUID) -> Customer | None:
        raise NotImplementedError

    async def create_customer(self, customer: Customer) -> Customer:
        raise NotImplementedError

    async def update_customer(self, customer: Customer) -> Customer:
        raise NotImplementedError

    async def delete_customer(self, id: UUID) -> None:
        raise NotImplementedError

    async def get_job(self, id: UUID) -> Job | None:
        raise NotImplementedError

    async def create_job(self, job: Job) -> Job:
        raise NotImplementedError

    async def update_job(self, job: Job) -> Job:
        raise NotImplementedError

    async def delete_job(self, id: UUID) -> None:
        raise NotImplementedError
