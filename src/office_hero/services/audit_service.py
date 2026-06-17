"""Audit event logging service — append-only, non-blocking."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from office_hero.core.logging import get_logger

log = get_logger(__name__)


class AuditService:
    """Service for writing immutable audit events to the audit_events table."""

    async def log_event(
        self,
        event_type: str,
        details: dict,
        tenant_id: UUID,
        session: AsyncSession,
        user_id: UUID | None = None,
        request_id: UUID | None = None,
    ) -> None:
        """Insert an audit event row.

        Args:
            event_type: Dot-notated event identifier (e.g. "auth.login").
            details: Arbitrary JSON-serialisable dict with event data.
            tenant_id: Tenant context for the event.
            session: Async SQLAlchemy session.
            user_id: Optional user who triggered the event.
            request_id: Optional HTTP request UUID for correlation.
        """
        if request_id is None:
            request_id = uuid4()

        stmt = text(
            """
            INSERT INTO audit_events (id, tenant_id, user_id, event_type, details, request_id)
            VALUES (:id, :tenant_id, :user_id, :event_type, :details, :request_id)
            """
        )
        await session.execute(
            stmt,
            {
                "id": str(uuid4()),
                "tenant_id": str(tenant_id),
                "user_id": str(user_id) if user_id else None,
                "event_type": event_type,
                "details": json.dumps(details),
                "request_id": str(request_id),
            },
        )
        log.debug(
            "audit_event.logged",
            event_type=event_type,
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
        )

    async def list_events(
        self,
        session: AsyncSession,
        *,
        tenant_id: str | None = None,
        event_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return a paginated slice of audit events with an accurate total count.

        Returns:
            (items, total) where items is a list of row dicts and total is the
            unfiltered-by-pagination count matching the filter predicates.
        """
        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
            "tenant_id": tenant_id,
            "event_type": event_type,
        }

        # NULL-safe predicates avoid f-string SQL construction.
        # When a filter param is None, the condition is always TRUE.
        count_result = await session.execute(
            text(
                "SELECT count(*) FROM audit_events"
                " WHERE (:tenant_id IS NULL OR tenant_id::text = :tenant_id)"
                " AND (:event_type IS NULL OR event_type = :event_type)"
            ),
            params,
        )
        total: int = count_result.scalar_one()

        rows_result = await session.execute(
            text(
                "SELECT id, timestamp, tenant_id, user_id, event_type, details, request_id"
                " FROM audit_events"
                " WHERE (:tenant_id IS NULL OR tenant_id::text = :tenant_id)"
                " AND (:event_type IS NULL OR event_type = :event_type)"
                " ORDER BY timestamp DESC"
                " LIMIT :limit OFFSET :offset"
            ),
            params,
        )
        items = [
            {
                "id": str(row.id),
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                "tenant_id": str(row.tenant_id),
                "user_id": str(row.user_id) if row.user_id else None,
                "event_type": row.event_type,
                "details": (
                    row.details
                    if isinstance(row.details, dict)
                    else json.loads(row.details or "{}")
                ),
                "request_id": str(row.request_id) if row.request_id else None,
            }
            for row in rows_result.mappings()
        ]
        return items, total
