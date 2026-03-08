from uuid import uuid4

import pytest

from office_hero.sagas import Saga


class DummyOutboxRepo:
    def __init__(self):
        self.events = []

    async def insert(self, event):
        self.events.append(event)
        return event


class DummySaga(Saga):
    pass


@pytest.mark.asyncio
async def test_enqueue_outbox_event_basic():
    repo = DummyOutboxRepo()
    tid = uuid4()
    saga = DummySaga(tenant_id=tid, outbox_repo=repo, saga_log_repo=None)

    ev = await saga.enqueue_outbox_event("foo", {"a": 1})
    assert ev["event_type"] == "foo"
    assert ev["tenant_id"] == tid
    assert "idem_key" in ev
    assert repo.events == [ev]


@pytest.mark.asyncio
async def test_enqueue_outbox_event_with_idem():
    repo = DummyOutboxRepo()
    tid = uuid4()
    saga = DummySaga(tenant_id=tid, outbox_repo=repo)
    key = uuid4()
    ev = await saga.enqueue_outbox_event("bar", {}, idem_key=key)
    assert ev["idem_key"] == key
    assert repo.events[0]["idem_key"] == key
