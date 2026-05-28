"""Job dispatch API route — POST /jobs/{job_id}/dispatch (Slice 14)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status

from office_hero.api.deps import require_permission
from office_hero.api.limiter import limiter
from office_hero.api.schemas.dispatch import JobDispatchRequest, JobDispatchResponse
from office_hero.core.exceptions import (
    InvalidJobTransitionError,
    JobNotFoundError,
    VehicleAlreadyBookedError,
    VehicleNotFoundError,
)
from office_hero.core.logging import get_logger

log = get_logger(__name__)

require_job_write = require_permission("job:write")
require_vehicle_read = require_permission("vehicle:read")


def _tenant_id(request: Request) -> UUID:
    raw = getattr(request.state, "tenant_id", None)
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return raw if isinstance(raw, UUID) else UUID(str(raw))


def create_dispatch_router(*, service_provider) -> APIRouter:
    """Construct the dispatch router with an injected service provider."""
    router = APIRouter()

    @router.post(
        "/jobs/{job_id}/dispatch",
        response_model=JobDispatchResponse,
        status_code=status.HTTP_200_OK,
        dependencies=[Depends(require_job_write), Depends(require_vehicle_read)],
    )
    @limiter.limit("60/minute")
    async def dispatch_job(
        request: Request,
        job_id: Annotated[UUID, Path()],
        body: JobDispatchRequest,
    ) -> JobDispatchResponse:
        """Assign a vehicle to a job and transition it to 'scheduled'."""
        tenant_id = _tenant_id(request)
        service = service_provider()

        try:
            job = await service.dispatch(
                tenant_id,
                job_id,
                vehicle_id=body.vehicle_id,
                scheduled_for=body.scheduled_for,
            )
        except JobNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=exc.message,
            ) from exc
        except VehicleNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=exc.message,
            ) from exc
        except InvalidJobTransitionError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=exc.message,
            ) from exc
        except VehicleAlreadyBookedError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=exc.message,
            ) from exc

        return JobDispatchResponse(
            id=job.id,
            status=job.status,
            assigned_vehicle_id=job.assigned_vehicle_id,
            scheduled_for=job.scheduled_for,
            title=job.title,
            customer_id=job.customer_id,
            location_id=job.location_id,
        )

    return router
