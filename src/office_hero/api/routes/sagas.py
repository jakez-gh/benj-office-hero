"""Saga state and management routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Path

from office_hero.sagas.core import SagaStatus

router = APIRouter()


# Response models
class SagaStateResponse:
    """Response for saga state query."""

    saga_id: UUID
    status: SagaStatus
    current_step: int
    context: dict
    last_error: str | None


@router.get(
    "/{saga_id}/state",
    response_model=dict,
    summary="Get saga state",
    description="Retrieve current saga status and context",
)
async def get_saga_state(saga_id: UUID = Path(..., description="Saga ID")) -> dict:  # noqa: B008
    """Get the current state of a saga.

    Returns saga ID, status (running/done/compensating/failed), current step index,
    context dict, and last error if any.

    **Future enhancement**: Inject SagaRepository to query saga from database.
    """
    raise HTTPException(
        status_code=501,
        detail="Not implemented: requires SagaRepository dependency injection",
    )


@router.post(
    "/{saga_id}/transition",
    response_model=dict,
    summary="Advance saga",
    description="Resume or advance saga execution (Operator only)",
)
async def transition_saga(saga_id: UUID = Path(..., description="Saga ID")) -> dict:  # noqa: B008
    """Transition saga to next state.

    Resumes saga execution from current step. Requires Operator RBAC.

    **Future enhancement**: Inject SagaService and enforce RBAC before calling.
    """
    raise HTTPException(
        status_code=501,
        detail="Not implemented: requires SagaService and RBAC",
    )


@router.post(
    "/{saga_id}/compensate",
    response_model=dict,
    summary="Manually compensate saga",
    description="Trigger manual compensation rollback (Operator only)",
)
async def compensate_saga(saga_id: UUID = Path(..., description="Saga ID")) -> dict:  # noqa: B008
    """Manually trigger saga compensation.

    Unwinds all completed steps in reverse order. Requires Operator RBAC.

    **Future enhancement**: Inject SagaService and enforce RBAC.
    """
    raise HTTPException(
        status_code=501,
        detail="Not implemented: requires SagaService and RBAC",
    )
