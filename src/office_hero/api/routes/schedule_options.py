"""Schedule-options API route — POST /jobs/{job_id}/schedule-options (Slice 13)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status

from office_hero.api.deps import require_permission
from office_hero.api.limiter import limiter
from office_hero.api.schemas.schedule_option import (
    ScheduleOptionItem,
    ScheduleOptionRequest,
    ScheduleOptionsResponse,
)
from office_hero.core.exceptions import JobNotFoundError, SchedulingNotAvailableError
from office_hero.core.logging import get_logger

log = get_logger(__name__)

require_job_read = require_permission("job:read")
require_vehicle_read = require_permission("vehicle:read")


def _tenant_id(request: Request) -> UUID:
    raw = getattr(request.state, "tenant_id", None)
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return raw if isinstance(raw, UUID) else UUID(str(raw))


def create_schedule_options_router(*, service_provider) -> APIRouter:
    """Construct the schedule-options router with an injected service provider."""
    router = APIRouter()

    @router.post(
        "/jobs/{job_id}/schedule-options",
        response_model=ScheduleOptionsResponse,
        dependencies=[Depends(require_job_read), Depends(require_vehicle_read)],
    )
    @limiter.limit("60/minute")
    async def get_schedule_options(
        request: Request,
        job_id: Annotated[UUID, Path()],
        body: ScheduleOptionRequest,
    ) -> ScheduleOptionsResponse:
        """Return ranked schedule suggestions for a job within a time window."""
        tenant_id = _tenant_id(request)
        service = service_provider()

        try:
            options = await service.get_options(
                tenant_id,
                job_id,
                window_start=body.window_start,
                window_end=body.window_end,
                max_results=body.max_results,
            )
        except JobNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=exc.message,
            ) from exc
        except SchedulingNotAvailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=exc.message,
            ) from exc

        return ScheduleOptionsResponse(
            job_id=job_id,
            options=[
                ScheduleOptionItem(
                    vehicle_id=opt.vehicle_id,
                    vehicle_display=opt.vehicle_display,
                    suggested_start=opt.suggested_start,
                    travel_seconds=opt.travel_seconds,
                    distance_meters=opt.distance_meters,
                    rank=opt.rank,
                )
                for opt in options
            ],
        )

    return router
