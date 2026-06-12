"""Integration tests for the SQL-backed outbox and saga repositories (Slice 24).

Runs against in-memory SQLite (aiosqlite) — the repos are dialect-agnostic
by design (string-36 ids, JSON columns, no Postgres-only operators).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from office_hero.models import Base
from office_hero.repositories.outbox_repository import SqlOutboxRepository
from office_hero.repositories.saga_repository import SqlSagaRepository
from office_hero.sagas.core import SagaStatus

TENANT_A = uuid4()
TENANT_B = uuid4()


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest_asyncio.fixture
async def outbox(session) -> SqlOutboxRepository:
    return SqlOutboxRepository(session)


@pytest_asyncio.fixture
async def saga_repo(session) -> SqlSagaRepository:
    return SqlSagaRepository(session)


# ---------------------------------------------------------------------------
# Outbox lifecycle
# ---------------------------------------------------------------------------


async def test_outbox_create_returns_pending_event(outbox):
    idem = uuid4()
    event = await outbox.create(
        TENANT_A, "backoffice.contract.created", {"contract_id": "c1"}, idem
    )
    assert event["status"] == "pending"
    assert event["attempt_count"] == 0
    assert event["idem_key"] == idem
    assert event["tenant_id"] == TENANT_A


async def test_outbox_get_pending_is_tenant_scoped_and_ordered(outbox):
    first = await outbox.create(TENANT_A, "e", {"n": 1}, uuid4())
    second = await outbox.create(TENANT_A, "e", {"n": 2}, uuid4())
    await outbox.create(TENANT_B, "e", {"n": 3}, uuid4())

    pending = await outbox.get_pending(TENANT_A, limit=10)
    assert [e["id"] for e in pending] == [first["id"], second["id"]]


async def test_outbox_full_lifecycle_processing_done(outbox):
    event = await outbox.create(TENANT_A, "e", {}, uuid4())
    await outbox.mark_processing(event["id"])
    assert await outbox.get_pending(TENANT_A) == []
    await outbox.mark_done(event["id"])

    done = await outbox.list_events(status="done", tenant_id=TENANT_A)
    assert len(done) == 1
    assert done[0]["processed_at"] is not None


async def test_outbox_dead_letter_and_retry(outbox):
    event = await outbox.create(TENANT_A, "e", {}, uuid4())
    assert await outbox.increment_attempt_count(event["id"]) == 1
    assert await outbox.increment_attempt_count(event["id"]) == 2
    await outbox.mark_dead_letter(event["id"], reason="adapter exploded")

    dead = await outbox.get_dead_letters(TENANT_A)
    assert len(dead) == 1
    assert dead[0]["dead_letter_reason"] == "adapter exploded"
    assert dead[0]["attempt_count"] == 2

    await outbox.retry_dead_letter(event["id"])
    retried = await outbox.get_pending(TENANT_A)
    assert len(retried) == 1
    assert retried[0]["attempt_count"] == 0
    assert retried[0]["dead_letter_reason"] is None


async def test_outbox_mark_pending_keeps_attempt_count(outbox):
    """The sync service requeues failures WITHOUT resetting the counter."""
    event = await outbox.create(TENANT_A, "e", {}, uuid4())
    await outbox.mark_processing(event["id"])
    await outbox.increment_attempt_count(event["id"])
    await outbox.mark_pending(event["id"])

    pending = await outbox.get_pending(TENANT_A)
    assert len(pending) == 1
    assert pending[0]["attempt_count"] == 1


async def test_outbox_list_events_filters(outbox):
    done_event = await outbox.create(TENANT_A, "e", {}, uuid4())
    await outbox.mark_done(done_event["id"])
    await outbox.create(TENANT_A, "e", {}, uuid4())
    await outbox.create(TENANT_B, "e", {}, uuid4())

    assert len(await outbox.list_events(tenant_id=TENANT_A)) == 2
    assert len(await outbox.list_events(status="pending", tenant_id=TENANT_A)) == 1
    assert len(await outbox.list_events(status="pending")) == 2


async def test_outbox_unknown_event_raises_key_error(outbox):
    with pytest.raises(KeyError):
        await outbox.mark_done(uuid4())


# ---------------------------------------------------------------------------
# Saga repository
# ---------------------------------------------------------------------------


async def test_saga_create_and_get_round_trip(saga_repo):
    ctx = await saga_repo.create(TENANT_A, "contract_sync", {"contract_id": "c1"})
    assert ctx.status is SagaStatus.RUNNING
    assert ctx.current_step == 0

    fetched = await saga_repo.get_by_id(ctx.saga_id)
    assert fetched is not None
    assert fetched.tenant_id == TENANT_A
    assert fetched.context == {"contract_id": "c1"}


async def test_saga_get_by_id_missing_returns_none(saga_repo):
    assert await saga_repo.get_by_id(uuid4()) is None


async def test_saga_update_status_merges_context_and_records_error(saga_repo):
    ctx = await saga_repo.create(TENANT_A, "contract_sync", {"a": 1})

    updated = await saga_repo.update_status(
        ctx.saga_id,
        SagaStatus.FAILED,
        context_update={"b": 2},
        error_msg="step 2 timed out",
    )
    assert updated.status is SagaStatus.FAILED
    assert updated.context == {"a": 1, "b": 2}
    assert updated.last_error == "step 2 timed out"


async def test_saga_update_current_step(saga_repo):
    ctx = await saga_repo.create(TENANT_A, "contract_sync", {})
    updated = await saga_repo.update_current_step(ctx.saga_id, 3)
    assert updated.current_step == 3


async def test_saga_get_by_type_and_context_filters(saga_repo):
    await saga_repo.create(TENANT_A, "contract_sync", {"contract_id": "c1"})
    await saga_repo.create(TENANT_A, "contract_sync", {"contract_id": "c2"})
    await saga_repo.create(TENANT_A, "job_sync", {"contract_id": "c1"})
    await saga_repo.create(TENANT_B, "contract_sync", {"contract_id": "c1"})

    matches = await saga_repo.get_by_type_and_context(
        TENANT_A, "contract_sync", {"contract_id": "c1"}
    )
    assert len(matches) == 1
    assert matches[0].context["contract_id"] == "c1"
