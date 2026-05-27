"""Unit tests for :class:`CustomerService` (TDD-first, no DB).

Audit redaction and tenant-defence are the security-critical behaviours; we
test those explicitly. Cross-tenant reads must return ``CustomerNotFoundError``
even when the caller knows the customer id (defence in depth on top of RLS).
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from office_hero.core.exceptions import CustomerNotFoundError
from office_hero.repositories.customer_repository import (
    InMemoryCustomerRepository,
)
from office_hero.repositories.mocks import InMemoryAuditService
from office_hero.services.customer_service import CustomerService


@pytest.fixture()
def repo() -> InMemoryCustomerRepository:
    """Fresh in-memory customer repository per test."""
    return InMemoryCustomerRepository()


@pytest.fixture()
def audit() -> InMemoryAuditService:
    """Fresh in-memory audit service per test."""
    return InMemoryAuditService()


@pytest.fixture()
def service(repo: InMemoryCustomerRepository, audit: InMemoryAuditService) -> CustomerService:
    """Service under test, wired to the in-memory deps."""
    return CustomerService(repo=repo, audit=audit)


@pytest.fixture()
def tenant_a():
    return uuid4()


@pytest.fixture()
def tenant_b():
    return uuid4()


@pytest.fixture()
def user_a():
    return uuid4()


@pytest.fixture()
def user_b():
    return uuid4()


async def test_create_customer_emits_audit_event(service, audit, tenant_a, user_a):
    """Creating a customer must emit ``customer.created`` with the new id."""
    cust = await service.create(
        tenant_id=tenant_a,
        user_id=user_a,
        name="Acme Plumbing",
        email="ops@acme.example",
    )

    assert cust.name == "Acme Plumbing"
    assert cust.tenant_id == tenant_a
    assert len(audit.events) == 1
    evt = audit.events[0]
    assert evt.event_type == "customer.created"
    assert evt.tenant_id == tenant_a
    assert evt.user_id == user_a
    assert evt.details["customer_id"] == str(cust.id)


async def test_update_customer_redacts_long_notes_in_audit(
    service, audit, tenant_a, user_a
):
    """Long ``notes`` fields are truncated in the audit details (ADR 063)."""
    cust = await service.create(tenant_id=tenant_a, user_id=user_a, name="Foo")
    long_notes = "x" * 500
    await service.update(
        tenant_id=tenant_a,
        user_id=user_a,
        customer_id=cust.id,
        patch={"notes": long_notes},
    )

    update_evt = next(e for e in audit.events if e.event_type == "customer.updated")
    after = update_evt.details["after"]
    assert "notes" in after
    assert after["notes"].endswith("[truncated]")
    assert len(after["notes"]) < len(long_notes)


async def test_archive_customer_sets_flag_and_audit(
    service, audit, tenant_a, user_a
):
    """Archive flips the flag, audit records the event."""
    cust = await service.create(tenant_id=tenant_a, user_id=user_a, name="Bar")
    archived = await service.archive(tenant_a, user_a, cust.id)

    assert archived.archived is True
    assert any(e.event_type == "customer.archived" for e in audit.events)


async def test_restore_customer_clears_flag_and_audit(
    service, audit, tenant_a, user_a
):
    """Restore unarchives and audits ``customer.restored``."""
    cust = await service.create(tenant_id=tenant_a, user_id=user_a, name="Baz")
    await service.archive(tenant_a, user_a, cust.id)
    restored = await service.restore(tenant_a, user_a, cust.id)

    assert restored.archived is False
    assert any(e.event_type == "customer.restored" for e in audit.events)


async def test_get_customer_cross_tenant_returns_not_found(
    service, repo, tenant_a, tenant_b, user_a
):
    """Defence-in-depth: cross-tenant read MUST raise CustomerNotFoundError."""
    cust = await service.create(tenant_id=tenant_a, user_id=user_a, name="Tenant A Co")
    with pytest.raises(CustomerNotFoundError):
        await service.get(tenant_b, cust.id)


async def test_list_customer_search_matches_name_substring(
    service, tenant_a, user_a
):
    """``search`` filter uses substring matching on name (case-insensitive)."""
    await service.create(tenant_id=tenant_a, user_id=user_a, name="Acme Plumbing")
    await service.create(tenant_id=tenant_a, user_id=user_a, name="Beta HVAC")
    await service.create(tenant_id=tenant_a, user_id=user_a, name="Acme Refrigeration")

    rows, total = await service.list(tenant_a, search="acme")
    assert total == 2
    names = sorted(r.name for r in rows)
    assert names == ["Acme Plumbing", "Acme Refrigeration"]


async def test_list_customer_tenant_isolation(
    service, tenant_a, tenant_b, user_a, user_b
):
    """``list`` only returns rows for the caller's tenant."""
    await service.create(tenant_id=tenant_a, user_id=user_a, name="A1")
    await service.create(tenant_id=tenant_a, user_id=user_a, name="A2")
    await service.create(tenant_id=tenant_b, user_id=user_b, name="B1")

    rows_a, total_a = await service.list(tenant_a)
    rows_b, total_b = await service.list(tenant_b)
    assert total_a == 2
    assert total_b == 1
    assert {r.name for r in rows_a} == {"A1", "A2"}
    assert {r.name for r in rows_b} == {"B1"}


async def test_update_unknown_customer_raises(service, tenant_a, user_a):
    """Updating a missing id surfaces :class:`CustomerNotFoundError`."""
    with pytest.raises(CustomerNotFoundError):
        await service.update(tenant_a, user_a, uuid4(), {"name": "ghost"})
