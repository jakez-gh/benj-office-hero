"""Unit tests for BackOfficeSyncService — outbox draining + dead-lettering (Slice 24)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from office_hero.repositories.customer_repository import InMemoryCustomerRepository
from office_hero.repositories.job_repository import InMemoryJobRepository
from office_hero.repositories.mocks import MockOutboxRepository
from office_hero.services.back_office_sync_service import MAX_ATTEMPTS, BackOfficeSyncService

TENANT_A = uuid4()
TENANT_B = uuid4()


@pytest.fixture()
def outbox() -> MockOutboxRepository:
    return MockOutboxRepository()


@pytest.fixture()
def svc(outbox) -> BackOfficeSyncService:
    return BackOfficeSyncService(
        outbox=outbox,
        customer_repo=InMemoryCustomerRepository(),
        job_repo=InMemoryJobRepository(),
    )


async def _enqueue_contract_event(outbox, *, tenant_id=TENANT_A) -> dict:
    contract_id = uuid4()
    return await outbox.create(
        tenant_id,
        event_type="backoffice.contract.created",
        payload={
            "contract_id": str(contract_id),
            "customer_id": str(uuid4()),
            "title": "Quarterly plan",
            "idem_key": str(contract_id),
        },
        idem_key=contract_id,
    )


async def test_process_pending_marks_contract_event_done(svc, outbox):
    event = await _enqueue_contract_event(outbox)

    counters = await svc.process_pending(TENANT_A)

    assert counters == {"processed": 1, "failed": 0, "dead_lettered": 0}
    assert outbox.events[event["id"]]["status"] == "done"
    assert outbox.events[event["id"]]["processed_at"] is not None


async def test_process_pending_scopes_to_tenant(svc, outbox):
    event = await _enqueue_contract_event(outbox, tenant_id=TENANT_B)

    counters = await svc.process_pending(TENANT_A)

    assert counters["processed"] == 0
    assert outbox.events[event["id"]]["status"] == "pending"


async def test_unknown_event_type_dead_letters_after_max_attempts(svc, outbox):
    event = await outbox.create(
        TENANT_A,
        event_type="backoffice.unsupported.thing",
        payload={"idem_key": str(uuid4())},
        idem_key=uuid4(),
    )

    for run in range(1, MAX_ATTEMPTS + 1):
        counters = await svc.process_pending(TENANT_A)
        if run < MAX_ATTEMPTS:
            assert counters["failed"] == 1
            assert outbox.events[event["id"]]["status"] == "pending"
            assert outbox.events[event["id"]]["attempt_count"] == run
        else:
            assert counters["dead_lettered"] == 1

    row = outbox.events[event["id"]]
    assert row["status"] == "dead"
    assert "No back-office handler" in row["dead_letter_reason"]

    # Dead events are not picked up again.
    assert (await svc.process_pending(TENANT_A))["processed"] == 0


async def test_operator_retry_resets_attempts_and_reprocesses(outbox):
    """A retried dead-letter goes through the full attempt budget again."""

    class _ExplodingAdapterService(BackOfficeSyncService):
        pass

    event = await outbox.create(
        TENANT_A,
        event_type="backoffice.unsupported.thing",
        payload={"idem_key": str(uuid4())},
        idem_key=uuid4(),
    )
    svc = _ExplodingAdapterService(
        outbox=outbox,
        customer_repo=InMemoryCustomerRepository(),
        job_repo=InMemoryJobRepository(),
    )
    for _ in range(MAX_ATTEMPTS):
        await svc.process_pending(TENANT_A)
    assert outbox.events[event["id"]]["status"] == "dead"

    await outbox.retry_dead_letter(event["id"])
    assert outbox.events[event["id"]]["status"] == "pending"
    assert outbox.events[event["id"]]["attempt_count"] == 0


async def test_customer_created_event_routes_to_adapter(svc, outbox):
    event = await outbox.create(
        TENANT_A,
        event_type="backoffice.customer.created",
        payload={"customer_id": str(uuid4()), "name": "Acme", "idem_key": str(uuid4())},
        idem_key=uuid4(),
    )

    counters = await svc.process_pending(TENANT_A)

    assert counters["processed"] == 1
    assert outbox.events[event["id"]]["status"] == "done"


async def test_tenant_repo_resolves_adapter_name(outbox):
    """The tenant's back_office_adapter column drives registry resolution."""

    class _Tenant:
        back_office_adapter = "native"

    class _TenantRepo:
        async def get_by_id(self, tenant_id):
            return _Tenant()

    svc = BackOfficeSyncService(
        outbox=outbox,
        customer_repo=InMemoryCustomerRepository(),
        job_repo=InMemoryJobRepository(),
        tenant_repo=_TenantRepo(),
    )
    await _enqueue_contract_event(outbox)
    assert (await svc.process_pending(TENANT_A))["processed"] == 1
