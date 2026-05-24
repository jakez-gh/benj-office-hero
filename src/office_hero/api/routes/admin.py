"""Admin routes for dead-letter, saga management, and audit events."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query

router = APIRouter()


# ---------------------------------------------------------------------------
# Audit Events — Slice 4 (Observability)
# ---------------------------------------------------------------------------


@router.get(
    "/audit-events",
    response_model=dict,
    summary="List audit events",
    description="Paginated, filterable audit event listing for admin panel",
)
async def list_audit_events(
    limit: int = Query(50, ge=1, le=1000, description="Max results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    event_type: str | None = Query(None, description="Filter by event type"),
    tenant_id: str | None = Query(None, description="Filter by tenant ID"),
) -> dict:
    """List audit events with pagination and optional filters.

    Returns paginated audit events from the append-only audit_events table.
    Supports filtering by event_type and tenant_id for efficient admin
    investigation.

    **Note:** DB-backed query wired when async session is available in
    the admin dependency. Returns an empty result set until then.
    """
    # TODO: Wire real DB query via AuditService when session is injected.
    # For now, return the contract shape so the admin panel can bind to it.
    return {
        "items": [],
        "total": 0,
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/dead-letters",
    response_model=dict,
    summary="List dead-letter events",
    description="Retrieve failed outbox events (Operator only)",
)
async def list_dead_letters(
    limit: int = Query(50, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Result offset"),
) -> dict:
    """List all dead-lettered events.

    Returns events that failed processing after max retries.
    Paginated with limit and offset.

    **Future enhancement**: Query OutboxRepository for dead-letter events.
    """
    raise HTTPException(
        status_code=501,
        detail="Not implemented: requires OutboxRepository and RBAC",
    )


@router.post(
    "/dead-letters/{event_id}/retry",
    response_model=dict,
    summary="Retry dead-letter event",
    description="Move failed event back to pending (Operator only)",
)
async def retry_dead_letter(
    event_id: UUID = Path(..., description="Event ID"),  # noqa: B008
) -> dict:
    """Retry a dead-lettered event.

    Resets attempt count to 0 and moves event back to pending status
    for reprocessing by outbox poller.

    **Future enhancement**: Update OutboxRepository and invoke poller.
    """
    raise HTTPException(
        status_code=501,
        detail="Not implemented: requires OutboxRepository and RBAC",
    )


@router.get(
    "/sagas/{saga_id}/logs",
    response_model=dict,
    summary="Get saga execution log",
    description="Retrieve detailed saga step execution history (Operator only)",
)
async def get_saga_logs(
    saga_id: UUID = Path(..., description="Saga ID"),  # noqa: B008
) -> dict:
    """Retrieve saga execution log.

    Shows detailed step-by-step execution and compensation history
    including timing and error details.

    **Future enhancement**: Query saga_log table; enforce RBAC.
    """
    raise HTTPException(
        status_code=501,
        detail="Not implemented: requires saga_log table query and RBAC",
    )
