"""Repository protocols for saga execution and outbox event management."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from office_hero.sagas.core import SagaContext, SagaStatus


class SagaRepository(Protocol):
    """Repository for persisting saga execution state.

    All methods are async; the concrete implementation uses SQLAlchemy
    AsyncSession for database access.
    """

    async def create(self, tenant_id: UUID, saga_type: str, context: dict[str, Any]) -> SagaContext:
        """Create a new saga execution record.

        Returns the SagaContext with saga_id populated.
        """
        ...

    async def get_by_id(self, saga_id: UUID) -> SagaContext | None:
        """Retrieve a saga by its ID."""
        ...

    async def get_by_type_and_context(
        self,
        tenant_id: UUID,
        saga_type: str,
        context_filter: dict[str, Any],
    ) -> list[SagaContext]:
        """Find sagas matching a saga_type and context criteria.

        Used to find an existing saga (e.g., for idempotency) rather than
        create a new one.
        """
        ...

    async def update_status(
        self,
        saga_id: UUID,
        new_status: SagaStatus,
        context_update: dict[str, Any] | None = None,
        error_msg: str | None = None,
    ) -> SagaContext:
        """Update the status of a saga.

        If context_update is provided, it is merged into the saga context.
        If error_msg is provided, it is stored in last_error.
        """
        ...

    async def update_current_step(self, saga_id: UUID, step_number: int) -> SagaContext:
        """Advance the current_step counter."""
        ...


class OutboxRepository(Protocol):
    """Repository for managing transactional outbox events.

    The outbox pattern ensures reliable saga step triggering:
    1. Domain write + outbox event write happen in one transaction
    2. Background poller reads pending events and processes them
    3. On success, event is marked done; on exhausted retries, moved to dead-letter
    """

    async def create(
        self,
        tenant_id: UUID,
        event_type: str,
        payload: dict[str, Any],
        idem_key: UUID,
    ) -> dict[str, Any]:
        """Create a new outbox event (status='pending').

        Returns the event dict with id and created_at populated.
        """
        ...

    async def get_pending(self, tenant_id: UUID, limit: int = 10) -> list[dict[str, Any]]:
        """Retrieve up to `limit` pending events for a tenant, ordered by created_at."""
        ...

    async def mark_processing(self, event_id: UUID) -> None:
        """Mark an event as 'processing' to prevent concurrent handling."""
        ...

    async def mark_done(self, event_id: UUID) -> None:
        """Mark an event as 'done' (status='done')."""
        ...

    async def mark_dead_letter(self, event_id: UUID, reason: str) -> None:
        """Mark an event as dead-lettered (status='dead') with a reason."""
        ...

    async def increment_attempt_count(self, event_id: UUID) -> int:
        """Increment the attempt count and return the new value.

        Used to implement exponential backoff or exhaustion limits.
        """
        ...

    async def get_dead_letters(self, tenant_id: UUID) -> list[dict[str, Any]]:
        """Retrieve all dead-lettered events for a tenant."""
        ...

    async def retry_dead_letter(self, event_id: UUID) -> None:
        """Move a dead-lettered event back to 'pending' for retry."""
        ...
