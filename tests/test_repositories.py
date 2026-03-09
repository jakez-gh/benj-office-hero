"""Tests for saga and outbox repositories (mock implementations)."""

from uuid import uuid4

import pytest

from office_hero.repositories.mocks import (
    MockOutboxRepository,
    MockSagaRepository,
)
from office_hero.sagas.core import SagaStatus


@pytest.mark.asyncio
async def test_mock_saga_repository_create():
    """MockSagaRepository creates and retrieves saga contexts."""
    repo = MockSagaRepository()
    tenant_id = uuid4()

    ctx = await repo.create(
        tenant_id=tenant_id,
        saga_type="test_saga",
        context={"key": "value"},
    )

    assert ctx.saga_id is not None
    assert ctx.tenant_id == tenant_id
    assert ctx.saga_type == "test_saga"
    assert ctx.status == SagaStatus.RUNNING
    assert ctx.context == {"key": "value"}


@pytest.mark.asyncio
async def test_mock_saga_repository_get_by_id():
    """MockSagaRepository retrieves saga by ID."""
    repo = MockSagaRepository()
    tenant_id = uuid4()

    created = await repo.create(
        tenant_id=tenant_id,
        saga_type="test",
        context={"a": 1},
    )

    retrieved = await repo.get_by_id(created.saga_id)
    assert retrieved is not None
    assert retrieved.saga_id == created.saga_id


@pytest.mark.asyncio
async def test_mock_saga_repository_update_status():
    """MockSagaRepository updates saga status."""
    repo = MockSagaRepository()
    tenant_id = uuid4()

    ctx = await repo.create(
        tenant_id=tenant_id,
        saga_type="test",
        context={},
    )

    updated = await repo.update_status(
        saga_id=ctx.saga_id,
        new_status=SagaStatus.DONE,
        context_update={"result": "success"},
    )

    assert updated.status == SagaStatus.DONE
    assert updated.context == {"result": "success"}


@pytest.mark.asyncio
async def test_mock_saga_repository_update_current_step():
    """MockSagaRepository advances current_step."""
    repo = MockSagaRepository()
    tenant_id = uuid4()

    ctx = await repo.create(
        tenant_id=tenant_id,
        saga_type="test",
        context={},
    )

    updated = await repo.update_current_step(
        saga_id=ctx.saga_id,
        step_number=2,
    )

    assert updated.current_step == 2


@pytest.mark.asyncio
async def test_mock_outbox_repository_create():
    """MockOutboxRepository creates outbox events."""
    repo = MockOutboxRepository()
    tenant_id = uuid4()
    idem_key = uuid4()

    event = await repo.create(
        tenant_id=tenant_id,
        event_type="customer_synced",
        payload={"customer_id": "123"},
        idem_key=idem_key,
    )

    assert event["id"] is not None
    assert event["tenant_id"] == tenant_id
    assert event["event_type"] == "customer_synced"
    assert event["status"] == "pending"
    assert event["idem_key"] == idem_key


@pytest.mark.asyncio
async def test_mock_outbox_repository_get_pending():
    """MockOutboxRepository retrieves pending events."""
    repo = MockOutboxRepository()
    tenant_id = uuid4()

    event1 = await repo.create(
        tenant_id=tenant_id,
        event_type="event1",
        payload={},
        idem_key=uuid4(),
    )
    event2 = await repo.create(
        tenant_id=tenant_id,
        event_type="event2",
        payload={},
        idem_key=uuid4(),
    )

    pending = await repo.get_pending(tenant_id, limit=10)
    assert len(pending) == 2
    assert pending[0]["id"] == event1["id"]
    assert pending[1]["id"] == event2["id"]


@pytest.mark.asyncio
async def test_mock_outbox_repository_mark_done():
    """MockOutboxRepository marks events as done."""
    repo = MockOutboxRepository()
    tenant_id = uuid4()

    event = await repo.create(
        tenant_id=tenant_id,
        event_type="test",
        payload={},
        idem_key=uuid4(),
    )

    await repo.mark_done(event["id"])

    assert repo.events[event["id"]]["status"] == "done"
    assert repo.events[event["id"]]["processed_at"] is not None


@pytest.mark.asyncio
async def test_mock_outbox_repository_mark_dead_letter():
    """MockOutboxRepository moves events to dead-letter."""
    repo = MockOutboxRepository()
    tenant_id = uuid4()

    event = await repo.create(
        tenant_id=tenant_id,
        event_type="test",
        payload={},
        idem_key=uuid4(),
    )

    await repo.mark_dead_letter(event["id"], "max retries exceeded")

    dead = repo.events[event["id"]]
    assert dead["status"] == "dead"
    assert dead["dead_letter_reason"] == "max retries exceeded"


@pytest.mark.asyncio
async def test_mock_outbox_repository_get_dead_letters():
    """MockOutboxRepository retrieves dead-lettered events."""
    repo = MockOutboxRepository()
    tenant_id = uuid4()

    event = await repo.create(
        tenant_id=tenant_id,
        event_type="test",
        payload={},
        idem_key=uuid4(),
    )

    await repo.mark_dead_letter(event["id"], "error")

    dead_letters = await repo.get_dead_letters(tenant_id)
    assert len(dead_letters) == 1
    assert dead_letters[0]["status"] == "dead"


@pytest.mark.asyncio
async def test_mock_outbox_repository_retry_dead_letter():
    """MockOutboxRepository retries dead-lettered events."""
    repo = MockOutboxRepository()
    tenant_id = uuid4()

    event = await repo.create(
        tenant_id=tenant_id,
        event_type="test",
        payload={},
        idem_key=uuid4(),
    )

    await repo.mark_dead_letter(event["id"], "error")
    await repo.retry_dead_letter(event["id"])

    retried = repo.events[event["id"]]
    assert retried["status"] == "pending"
    assert retried["attempt_count"] == 0
