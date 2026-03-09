"""Audit event logging service — append-only, non-blocking."""

from __future__ import annotations

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
                "details": details,
                "request_id": str(request_id),
            },
        )
        log.debug(
            "audit_event.logged",
            event_type=event_type,
            tenant_id=str(tenant_id),
            user_id=str(user_id) if user_id else None,
        )
