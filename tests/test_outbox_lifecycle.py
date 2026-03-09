"""Outbox pattern tests for eventual consistency."""

from uuid import uuid4

import pytest

from office_hero.repositories.mocks import MockOutboxRepository


@pytest.fixture
def outbox_repo():
    """Provide mock outbox repository."""
    return MockOutboxRepository()


@pytest.mark.asyncio
async def test_outbox_event_lifecycle(outbox_repo):
    """Test complete outbox event lifecycle: create, pending, processing, done."""
    tenant_id = uuid4()
    idem_key = uuid4()

    # Create event
    event = await outbox_repo.create(
        tenant_id=tenant_id,
        event_type="customer.created",
        payload={"name": "John", "email": "john@example.com"},
        idem_key=idem_key,
    )
    event_id = event["id"]
    assert event["status"] == "pending"
    assert event["attempt_count"] == 0

    # Get pending events
    pending = await outbox_repo.get_pending(tenant_id=tenant_id, limit=10)
    assert len(pending) >= 1
    assert any(e["id"] == event_id for e in pending)

    # Mark as processing
    await outbox_repo.mark_processing(event_id)
    stored = outbox_repo.events[event_id]
    assert stored["status"] == "processing"

    # Mark as done
    await outbox_repo.mark_done(event_id)
    stored = outbox_repo.events[event_id]
    assert stored["status"] == "done"
    assert stored["processed_at"] is not None


@pytest.mark.asyncio
async def test_outbox_dead_letter_flow(outbox_repo):
    """Test outbox event dead-lettering after max retries."""
    tenant_id = uuid4()
    idem_key = uuid4()

    event = await outbox_repo.create(
        tenant_id=tenant_id,
        event_type="error.event",
        payload={"error": "upstream_service_down"},
        idem_key=idem_key,
    )
    event_id = event["id"]
    assert event["status"] == "pending"

    # Increment attempt count to simulate failures
    for _ in range(5):
        await outbox_repo.increment_attempt_count(event_id)

    # Move to dead-letter after max attempts
    await outbox_repo.mark_dead_letter(event_id, "max_retries_exceeded")
    dead_event = outbox_repo.events[event_id]
    assert dead_event["status"] == "dead"
    assert dead_event["dead_letter_reason"] == "max_retries_exceeded"


@pytest.mark.asyncio
async def test_outbox_retry_dead_letter(outbox_repo):
    """Test retrying a dead-lettered event."""
    tenant_id = uuid4()
    idem_key = uuid4()

    event = await outbox_repo.create(
        tenant_id=tenant_id,
        event_type="job.sync",
        payload={"job_id": "12345"},
        idem_key=idem_key,
    )
    event_id = event["id"]

    # Move to dead-letter
    await outbox_repo.mark_dead_letter(event_id, "network_timeout")
    dead = await outbox_repo.get_dead_letters(tenant_id=tenant_id)
    assert any(e["id"] == event_id for e in dead)

    # Retry dead-letter (reset to pending)
    await outbox_repo.retry_dead_letter(event_id)
    retried = outbox_repo.events[event_id]
    assert retried["status"] == "pending"
    assert retried["attempt_count"] == 0


@pytest.mark.asyncio
async def test_outbox_attempt_count_increments(outbox_repo):
    """Test attempt count increments properly."""
    tenant_id = uuid4()
    idem_key = uuid4()

    event = await outbox_repo.create(
        tenant_id=tenant_id,
        event_type="sync.event",
        payload={"data": "test"},
        idem_key=idem_key,
    )
    event_id = event["id"]
    assert event["attempt_count"] == 0

    for expected_count in range(1, 4):
        count = await outbox_repo.increment_attempt_count(event_id)
        assert count == expected_count


@pytest.mark.asyncio
async def test_outbox_get_dead_letters_list(outbox_repo):
    """Test dead-letter listing retrieves all dead-lettered events."""
    tenant_id = uuid4()

    # Create 5 dead-lettered events
    event_ids = []
    for i in range(5):
        idem_key = uuid4()
        event = await outbox_repo.create(
            tenant_id=tenant_id,
            event_type=f"event_{i}",
            payload={"index": i},
            idem_key=idem_key,
        )
        event_ids.append(event["id"])
        await outbox_repo.mark_dead_letter(event["id"], f"reason_{i}")

    # Get dead-letters for this tenant
    dead_letters = await outbox_repo.get_dead_letters(tenant_id=tenant_id)
    assert len(dead_letters) == 5
    assert all(d["id"] in event_ids for d in dead_letters)


@pytest.mark.asyncio
async def test_outbox_event_with_large_payload(outbox_repo):
    """Test outbox handles large event payloads."""
    tenant_id = uuid4()
    idem_key = uuid4()

    large_payload = {f"field_{i}": f"value_{i}" * 100 for i in range(50)}

    event = await outbox_repo.create(
        tenant_id=tenant_id,
        event_type="large.event",
        payload=large_payload,
        idem_key=idem_key,
    )
    assert len(event["payload"]) == 50
    assert all(event["payload"][f"field_{i}"] == f"value_{i}" * 100 for i in range(50))


@pytest.mark.asyncio
async def test_outbox_multiple_concurrent_events(outbox_repo):
    """Test multiple events created for same tenant."""
    tenant_id = uuid4()
    idem_keys = [uuid4() for _ in range(3)]

    for i, idem_key in enumerate(idem_keys):
        await outbox_repo.create(
            tenant_id=tenant_id,
            event_type=f"event_type_{i}",
            payload={"order": i},
            idem_key=idem_key,
        )

    # All should be pending
    pending = await outbox_repo.get_pending(tenant_id=tenant_id, limit=10)
    assert len(pending) == 3
    assert all(p["status"] == "pending" for p in pending)


@pytest.mark.asyncio
async def test_outbox_events_isolated_by_tenant(outbox_repo):
    """Test events from different tenants are isolated."""
    tenant1 = uuid4()
    tenant2 = uuid4()

    # Create event for tenant 1
    event1 = await outbox_repo.create(
        tenant_id=tenant1,
        event_type="event.type1",
        payload={"tenant": "1"},
        idem_key=uuid4(),
    )

    # Create event for tenant 2
    event2 = await outbox_repo.create(
        tenant_id=tenant2,
        event_type="event.type2",
        payload={"tenant": "2"},
        idem_key=uuid4(),
    )

    # Tenant 1 should only see their event
    tenant1_pending = await outbox_repo.get_pending(tenant_id=tenant1, limit=10)
    assert len(tenant1_pending) == 1
    assert tenant1_pending[0]["id"] == event1["id"]

    # Tenant 2 should only see their event
    tenant2_pending = await outbox_repo.get_pending(tenant_id=tenant2, limit=10)
    assert len(tenant2_pending) == 1
    assert tenant2_pending[0]["id"] == event2["id"]
