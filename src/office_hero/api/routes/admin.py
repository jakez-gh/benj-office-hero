"""Admin routes for dead-letter and saga management."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Path, Query

router = APIRouter()


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
