"""Unit tests for the NativeAdapter + back-office adapter registry (Slice 24)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from office_hero.adapters.back_office import BackOfficeAdapter, Customer, Job, NativeAdapter
from office_hero.adapters.back_office.registry import (
    UnknownBackOfficeAdapterError,
    get_adapter_factory,
    known_adapters,
)
from office_hero.repositories.customer_repository import InMemoryCustomerRepository
from office_hero.repositories.job_repository import InMemoryJobRepository

TENANT_A = uuid4()
TENANT_B = uuid4()
USER_A = uuid4()


@pytest.fixture()
def cust_repo() -> InMemoryCustomerRepository:
    return InMemoryCustomerRepository()


@pytest.fixture()
def job_repo() -> InMemoryJobRepository:
    return InMemoryJobRepository()


@pytest.fixture()
def adapter(cust_repo, job_repo) -> NativeAdapter:
    return NativeAdapter(TENANT_A, cust_repo, job_repo)


async def test_native_adapter_satisfies_protocol(adapter):
    assert isinstance(adapter, BackOfficeAdapter)


async def test_health_check_true(adapter):
    assert await adapter.health_check() is True


async def test_get_customer_returns_local_row(adapter, cust_repo):
    row = await cust_repo.create(TENANT_A, name="Acme Plumbing")
    result = await adapter.get_customer(row.id)
    assert result == Customer(id=row.id, name="Acme Plumbing")


async def test_get_customer_cross_tenant_returns_none(adapter, cust_repo):
    """Tenant B's customer is invisible through tenant A's adapter."""
    row = await cust_repo.create(TENANT_B, name="Other Co")
    assert await adapter.get_customer(row.id) is None


async def test_get_job_returns_local_row(adapter, job_repo):
    row = await job_repo.create(
        TENANT_A,
        customer_id=uuid4(),
        location_id=uuid4(),
        industry="plumbing",
        title="Fix pipe",
        created_by_user_id=USER_A,
    )
    result = await adapter.get_job(row.id)
    assert result == Job(id=row.id, customer_id=row.customer_id)


async def test_create_and_update_are_idempotent_acknowledgements(adapter):
    """Native writes acknowledge — Office Hero already persisted the row."""
    customer = Customer(id=uuid4(), name="Acme")
    job = Job(id=uuid4(), customer_id=customer.id)
    assert await adapter.create_customer(customer) == customer
    assert await adapter.update_customer(customer) == customer
    assert await adapter.create_job(job) == job
    assert await adapter.update_job(job) == job
    assert await adapter.delete_customer(customer.id) is None
    assert await adapter.delete_job(job.id) is None


def test_registry_resolves_native(cust_repo, job_repo):
    factory = get_adapter_factory("native")
    adapter = factory(TENANT_A, cust_repo, job_repo)
    assert isinstance(adapter, NativeAdapter)


def test_registry_unknown_name_raises():
    with pytest.raises(UnknownBackOfficeAdapterError):
        get_adapter_factory("salesforce")


def test_known_adapters_lists_native():
    assert "native" in known_adapters()
