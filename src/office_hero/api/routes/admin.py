"""Admin routes for dead-letter and saga management.

Provides:
  - GET /admin/dead-letters — list dead-letter (failed) outbox events
  - POST /admin/dead-letters/{event_id}/retry — reset dead-letter to pending
  - GET /admin/sagas/{saga_id}/logs — retrieve saga execution history
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel

from office_hero.repositories.protocols import OutboxRepository
from office_hero.services.saga_service import SagaService


class DeadLetterItem(BaseModel):
    """Single dead-letter event in the list response."""

    id: str
    tenant_id: str
    event_type: str
    payload: dict
    status: str
    attempt_count: int
    created_at: str | None = None
    processed_at: str | None = None
    dead_letter_reason: str | None = None


class DeadLetterListResponse(BaseModel):
    """Paginated dead-letter list response."""

    items: list[DeadLetterItem]
    total: int
    limit: int
    offset: int


class DeadLetterRetryResponse(BaseModel):
    """Response after retrying a dead-letter event."""

    id: str
    status: str
    message: str


class SagaLogResponse(BaseModel):
    """Saga execution log response."""

    saga_id: str
    saga_type: str
    status: str
    current_step: int
    context: dict
    last_error: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


def create_admin_router(
    *,
    saga_service: SagaService,
    outbox_repo: OutboxRepository,
) -> APIRouter:
    """Factory that creates admin routes with injected dependencies (DI)."""
    router = APIRouter()

    @router.get(
        "/dead-letters",
        response_model=DeadLetterListResponse,
        summary="List dead-letter events",
        description="Retrieve failed outbox events (Operator only)",
    )
    async def list_dead_letters(
        limit: int = Query(50, ge=1, le=1000, description="Max results"),
        offset: int = Query(0, ge=0, description="Result offset"),
    ) -> DeadLetterListResponse:
        """List all dead-lettered events across all tenants (Operator view)."""
        # Collect all dead-letter events from all tenants
        all_dead = []
        for event in outbox_repo.events.values():
            if event.get("status") == "dead":
                all_dead.append(event)

        # Sort by created_at descending (newest first)
        all_dead.sort(key=lambda e: e.get("created_at", ""), reverse=True)

        total = len(all_dead)
        page = all_dead[offset : offset + limit]

        items = [
            DeadLetterItem(
                id=str(evt["id"]),
                tenant_id=str(evt["tenant_id"]),
                event_type=evt["event_type"],
                payload=evt["payload"],
                status=evt["status"],
                attempt_count=evt["attempt_count"],
                created_at=evt.get("created_at"),
                processed_at=evt.get("processed_at"),
                dead_letter_reason=evt.get("dead_letter_reason"),
            )
            for evt in page
        ]

        return DeadLetterListResponse(
            items=items, total=total, limit=limit, offset=offset
        )

    @router.post(
        "/dead-letters/{event_id}/retry",
        response_model=DeadLetterRetryResponse,
        summary="Retry dead-letter event",
        description="Move failed event back to pending (Operator only)",
    )
    async def retry_dead_letter(
        event_id: Annotated[UUID, Path(description="Event ID")],
    ) -> DeadLetterRetryResponse:
        """Retry a dead-lettered event — reset to pending for reprocessing."""
        event = outbox_repo.events.get(event_id)
        if event is None:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found")

        if event.get("status") != "dead":
            raise HTTPException(
                status_code=400,
                detail=f"Event {event_id} is not in dead-letter state (current: {event.get('status')})",
            )

        await outbox_repo.retry_dead_letter(event_id)

        return DeadLetterRetryResponse(
            id=str(event_id),
            status="pending",
            message="Event reset to pending for reprocessing",
        )

    @router.get(
        "/sagas/{saga_id}/logs",
        response_model=SagaLogResponse,
        summary="Get saga execution log",
        description="Retrieve detailed saga step execution history (Operator only)",
    )
    async def get_saga_logs(
        saga_id: Annotated[UUID, Path(description="Saga ID")],
    ) -> SagaLogResponse:
        """Retrieve saga execution log and current state."""
        saga_ctx = await saga_service.get_saga_status(saga_id)
        if saga_ctx is None:
            raise HTTPException(status_code=404, detail=f"Saga {saga_id} not found")

        return SagaLogResponse(
            saga_id=str(saga_ctx.saga_id),
            saga_type=saga_ctx.saga_type,
            status=saga_ctx.status.value
            if hasattr(saga_ctx.status, "value")
            else str(saga_ctx.status),
            current_step=saga_ctx.current_step,
            context=saga_ctx.context,
            last_error=saga_ctx.last_error,
            created_at=saga_ctx.created_at,
            updated_at=saga_ctx.updated_at,
        )

    return router
