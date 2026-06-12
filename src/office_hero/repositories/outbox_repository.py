"""SQL-backed outbox repository (ADR 056, Slice 24).

Implements :class:`office_hero.repositories.protocols.OutboxRepository`
against the ``outbox_events`` table.  The legacy table stores string-36
ids; this repository accepts/returns :class:`uuid.UUID` (or str) and
converts at the boundary so callers and the in-memory mock stay
interchangeable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from office_hero.models.outbox_event import OutboxEvent


def _row_to_dict(row: OutboxEvent) -> dict[str, Any]:
    """Project an ORM row onto the protocol's event-dict shape."""
    return {
        "id": UUID(row.id),
        "tenant_id": UUID(row.tenant_id),
        "event_type": row.event_type,
        "payload": row.payload,
        "idem_key": UUID(row.idem_key),
        "status": row.status,
        "attempt_count": row.attempt_count,
        "dead_letter_reason": row.dead_letter_reason,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "processed_at": row.processed_at.isoformat() if row.processed_at else None,
    }


class SqlOutboxRepository:
    """SQLAlchemy-backed concrete :class:`OutboxRepository` (ADR 058)."""

    def __init__(self, session: AsyncSession) -> None:
        """Bind to an async SQLAlchemy session."""
        self.session = session

    async def _get(self, event_id: UUID) -> OutboxEvent:
        row = await self.session.get(OutboxEvent, str(event_id))
        if row is None:
            raise KeyError(f"Outbox event {event_id} not found")
        return row

    async def create(
        self,
        tenant_id: UUID,
        event_type: str,
        payload: dict[str, Any],
        idem_key: UUID,
    ) -> dict[str, Any]:
        """Insert a pending event; returns the protocol event dict."""
        row = OutboxEvent(
            tenant_id=str(tenant_id),
            event_type=event_type,
            payload=payload,
            idem_key=str(idem_key),
            status="pending",
            attempt_count=0,
        )
        self.session.add(row)
        await self.session.flush()
        return _row_to_dict(row)

    async def get_pending(self, tenant_id: UUID, limit: int = 10) -> list[dict[str, Any]]:
        """Oldest-first pending events for a tenant."""
        stmt = (
            select(OutboxEvent)
            .where(
                OutboxEvent.tenant_id == str(tenant_id),
                OutboxEvent.status == "pending",
            )
            .order_by(OutboxEvent.created_at.asc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [_row_to_dict(r) for r in rows]

    async def mark_processing(self, event_id: UUID) -> None:
        row = await self._get(event_id)
        row.status = "processing"
        await self.session.flush()

    async def mark_pending(self, event_id: UUID) -> None:
        row = await self._get(event_id)
        row.status = "pending"
        await self.session.flush()

    async def mark_done(self, event_id: UUID) -> None:
        row = await self._get(event_id)
        row.status = "done"
        row.processed_at = datetime.now(UTC).replace(tzinfo=None)
        await self.session.flush()

    async def mark_dead_letter(self, event_id: UUID, reason: str) -> None:
        row = await self._get(event_id)
        row.status = "dead"
        row.dead_letter_reason = reason
        row.processed_at = datetime.now(UTC).replace(tzinfo=None)
        await self.session.flush()

    async def increment_attempt_count(self, event_id: UUID) -> int:
        await self.session.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id == str(event_id))
            .values(attempt_count=OutboxEvent.attempt_count + 1)
        )
        row = await self._get(event_id)
        await self.session.refresh(row)
        return row.attempt_count

    async def get_dead_letters(self, tenant_id: UUID) -> list[dict[str, Any]]:
        stmt = (
            select(OutboxEvent)
            .where(
                OutboxEvent.tenant_id == str(tenant_id),
                OutboxEvent.status == "dead",
            )
            .order_by(OutboxEvent.created_at.asc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [_row_to_dict(r) for r in rows]

    async def retry_dead_letter(self, event_id: UUID) -> None:
        row = await self._get(event_id)
        row.status = "pending"
        row.attempt_count = 0
        row.dead_letter_reason = None
        await self.session.flush()

    async def list_events(
        self,
        *,
        status: str | None = None,
        tenant_id: UUID | str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Admin/operator enumeration with filters pushed down to SQL."""
        stmt = select(OutboxEvent)
        if status is not None:
            stmt = stmt.where(OutboxEvent.status == status)
        if tenant_id is not None:
            stmt = stmt.where(OutboxEvent.tenant_id == str(tenant_id))
        stmt = stmt.order_by(OutboxEvent.created_at.asc()).limit(limit).offset(offset)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [_row_to_dict(r) for r in rows]
