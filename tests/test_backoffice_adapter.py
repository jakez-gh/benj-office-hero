from uuid import UUID, uuid4

import pytest

from office_hero.adapters.back_office import (
    BackOfficeAdapter,
    Customer,
    Job,
    NativeAdapter,
)


class DummyAdapter:
    # implement every method from the protocol; signatures must match
    async def health_check(self) -> bool:
        return True

    async def get_customer(self, id: UUID) -> Customer | None:
        return None

    async def create_customer(self, customer: Customer) -> Customer:
        return customer

    async def update_customer(self, customer: Customer) -> Customer:
        return customer

    async def delete_customer(self, id: UUID) -> None:
        pass

    async def get_job(self, id: UUID) -> Job | None:
        return None

    async def create_job(self, job: Job) -> Job:
        return job

    async def update_job(self, job: Job) -> Job:
        return job

    async def delete_job(self, id: UUID) -> None:
        pass


def _native_adapter() -> NativeAdapter:
    """NativeAdapter is tenant-scoped since slice 24 (see test_native_adapter.py)."""
    from office_hero.repositories.customer_repository import InMemoryCustomerRepository
    from office_hero.repositories.job_repository import InMemoryJobRepository

    return NativeAdapter(uuid4(), InMemoryCustomerRepository(), InMemoryJobRepository())


@pytest.mark.asyncio
async def test_protocol_runtime_checkable():
    """The protocol should be checkable at runtime and accept conforming objects."""
    assert isinstance(DummyAdapter(), BackOfficeAdapter)
    assert isinstance(_native_adapter(), BackOfficeAdapter)


@pytest.mark.asyncio
async def test_health_check_default():
    adapter = _native_adapter()
    assert await adapter.health_check() is True


@pytest.mark.asyncio
async def test_adapter_method_signatures():
    # just call through to make sure the methods exist with expected parameter
    # types; nothing fancy yet.
    a = DummyAdapter()
    cust = Customer(id=uuid4(), name="x")
    job = Job(id=uuid4(), customer_id=uuid4())

    assert await a.create_customer(cust) is cust
    assert await a.update_customer(cust) is cust
    assert await a.create_job(job) is job
    assert await a.update_job(job) is job
