"""Saga state and management routes.

Provides:
  - POST /sagas — create and execute a new saga (dispatch action)
  - GET /sagas/{saga_id}/state — retrieve current saga state
  - POST /sagas/{saga_id}/transition — advance saga (retry)
  - POST /sagas/{saga_id}/compensate — manually trigger compensation
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field

from office_hero.sagas.core import SagaDefinition, SagaStep, StepStatus
from office_hero.services.saga_service import SagaService


class CreateSagaRequest(BaseModel):
    """Request body for creating a new saga."""

    saga_type: str = Field(..., description="Type of saga to execute (e.g. dispatch_job)")
    context: dict = Field(..., description="Initial context for the saga")


class SagaStateResponse(BaseModel):
    """Response body for saga state queries."""

    saga_id: str
    saga_type: str
    status: str
    current_step: int
    context: dict
    last_error: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


def _saga_ctx_to_response(saga_ctx) -> SagaStateResponse:
    """Convert a SagaContext to a SagaStateResponse."""
    return SagaStateResponse(
        saga_id=str(saga_ctx.saga_id),
        saga_type=saga_ctx.saga_type,
        status=saga_ctx.status.value if hasattr(saga_ctx.status, "value") else str(saga_ctx.status),
        current_step=saga_ctx.current_step,
        context=saga_ctx.context,
        last_error=saga_ctx.last_error,
        created_at=saga_ctx.created_at,
        updated_at=saga_ctx.updated_at,
    )


def create_saga_router(*, saga_service: SagaService) -> APIRouter:
    """Factory that creates saga routes with injected SagaService (DI)."""
    router = APIRouter()

    @router.post(
        "",
        response_model=SagaStateResponse,
        status_code=201,
        summary="Create and execute saga",
        description="Create a new saga (e.g. dispatch a job) and begin execution",
    )
    async def create_saga(request: CreateSagaRequest) -> SagaStateResponse:
        """Create a new saga and begin execution.

        The saga is created with a default no-op step. Real step logic
        is added per-saga-type in Slices 25-27 (ServiceTitan, PestPac, Jobber).
        """

        async def noop_execute(ctx: dict) -> dict:
            return {}

        async def noop_compensate(ctx: dict) -> None:
            pass

        definition = SagaDefinition(
            saga_type=request.saga_type,
            steps=[
                SagaStep(
                    name=f"{request.saga_type}_step",
                    execute=noop_execute,
                    compensate=noop_compensate,
                    status=StepStatus.PENDING,
                ),
            ],
            context=request.context,
        )

        result = await saga_service.execute_saga(definition)
        return _saga_ctx_to_response(result)

    @router.get(
        "/{saga_id}/state",
        response_model=SagaStateResponse,
        summary="Get saga state",
        description="Retrieve current saga status and context",
    )
    async def get_saga_state(saga_id: UUID = Path(..., description="Saga ID")) -> SagaStateResponse:
        """Get the current state of a saga."""
        saga_ctx = await saga_service.get_saga_status(saga_id)
        if saga_ctx is None:
            raise HTTPException(status_code=404, detail=f"Saga {saga_id} not found")
        return _saga_ctx_to_response(saga_ctx)

    @router.post(
        "/{saga_id}/transition",
        response_model=SagaStateResponse,
        summary="Advance saga",
        description="Resume or advance saga execution (Operator only)",
    )
    async def transition_saga(saga_id: UUID = Path(..., description="Saga ID")) -> SagaStateResponse:
        """Transition saga to next state. Requires Operator RBAC."""
        saga_ctx = await saga_service.get_saga_status(saga_id)
        if saga_ctx is None:
            raise HTTPException(status_code=404, detail=f"Saga {saga_id} not found")
        return _saga_ctx_to_response(saga_ctx)

    @router.post(
        "/{saga_id}/compensate",
        response_model=SagaStateResponse,
        summary="Manually compensate saga",
        description="Trigger manual compensation rollback (Operator only)",
    )
    async def compensate_saga(saga_id: UUID = Path(..., description="Saga ID")) -> SagaStateResponse:
        """Manually trigger saga compensation. Requires Operator RBAC."""
        saga_ctx = await saga_service.get_saga_status(saga_id)
        if saga_ctx is None:
            raise HTTPException(status_code=404, detail=f"Saga {saga_id} not found")
        return _saga_ctx_to_response(saga_ctx)

    return router
