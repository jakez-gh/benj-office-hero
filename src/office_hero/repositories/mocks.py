"""In-memory mock implementations of saga and outbox repositories for testing."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from office_hero.sagas.core import SagaContext, SagaStatus


class MockSagaRepository:
    """In-memory saga repository for unit testing."""

    def __init__(self):
        self.sagas: dict[UUID, SagaContext] = {}

    async def create(self, tenant_id: UUID, saga_type: str, context: dict[str, Any]) -> SagaContext:
        saga_id = uuid4()
        now = datetime.now(UTC).isoformat()
        ctx = SagaContext(
            saga_id=saga_id,
            tenant_id=tenant_id,
            saga_type=saga_type,
            current_step=0,
            status=SagaStatus.RUNNING,
            context=context,
            created_at=now,
            updated_at=now,
        )
        self.sagas[saga_id] = ctx
        return ctx

    async def get_by_id(self, saga_id: UUID) -> SagaContext | None:
        return self.sagas.get(saga_id)

    async def get_by_type_and_context(
        self,
        tenant_id: UUID,
        saga_type: str,
        context_filter: dict[str, Any],
    ) -> list[SagaContext]:
        results = []
        for ctx in self.sagas.values():
            # Match tenant_id, saga_type, and all context filter keys
            if (
                ctx.tenant_id == tenant_id
                and ctx.saga_type == saga_type
                and all(ctx.context.get(k) == v for k, v in context_filter.items())
            ):
                results.append(ctx)
        return results

    async def update_status(
        self,
        saga_id: UUID,
        new_status: SagaStatus,
        context_update: dict[str, Any] | None = None,
        error_msg: str | None = None,
    ) -> SagaContext:
        ctx = self.sagas[saga_id]
        ctx.status = new_status
        if context_update:
            ctx.context.update(context_update)
        if error_msg:
            ctx.last_error = error_msg
        ctx.updated_at = datetime.now(UTC).isoformat()
        return ctx

    async def update_current_step(self, saga_id: UUID, step_number: int) -> SagaContext:
        ctx = self.sagas[saga_id]
        ctx.current_step = step_number
        ctx.updated_at = datetime.now(UTC).isoformat()
        return ctx


class MockOutboxRepository:
    """In-memory outbox repository for unit testing."""

    def __init__(self):
        self.events: dict[UUID, dict[str, Any]] = {}

    async def create(
        self,
        tenant_id: UUID,
        event_type: str,
        payload: dict[str, Any],
        idem_key: UUID,
    ) -> dict[str, Any]:
        event_id = uuid4()
        now = datetime.now(UTC).isoformat()
        event = {
            "id": event_id,
            "tenant_id": tenant_id,
            "event_type": event_type,
            "payload": payload,
            "idem_key": idem_key,
            "status": "pending",
            "attempt_count": 0,
            "created_at": now,
            "processed_at": None,
        }
        self.events[event_id] = event
        return event

    async def get_pending(self, tenant_id: UUID, limit: int = 10) -> list[dict[str, Any]]:
        pending = [
            e
            for e in self.events.values()
            if e["tenant_id"] == tenant_id and e["status"] == "pending"
        ]
        return sorted(pending, key=lambda e: e["created_at"])[:limit]

    async def mark_processing(self, event_id: UUID) -> None:
        self.events[event_id]["status"] = "processing"

    async def mark_done(self, event_id: UUID) -> None:
        now = datetime.now(UTC).isoformat()
        self.events[event_id]["status"] = "done"
        self.events[event_id]["processed_at"] = now

    async def mark_dead_letter(self, event_id: UUID, reason: str) -> None:
        now = datetime.now(UTC).isoformat()
        self.events[event_id]["status"] = "dead"
        self.events[event_id]["dead_letter_reason"] = reason
        self.events[event_id]["processed_at"] = now

    async def increment_attempt_count(self, event_id: UUID) -> int:
        self.events[event_id]["attempt_count"] += 1
        return self.events[event_id]["attempt_count"]

    async def get_dead_letters(self, tenant_id: UUID) -> list[dict[str, Any]]:
        return [
            e for e in self.events.values() if e["tenant_id"] == tenant_id and e["status"] == "dead"
        ]

    async def retry_dead_letter(self, event_id: UUID) -> None:
        self.events[event_id]["status"] = "pending"
        self.events[event_id]["attempt_count"] = 0
