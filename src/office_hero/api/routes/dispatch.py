"""Job dispatch API route — POST /jobs/{job_id}/dispatch (Slice 14)."""

from __future__ import annotations

from datetime import UTC, datetime, time
from typing import Annotated, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status

from office_hero.api.deps import require_permission
from office_hero.api.limiter import limiter
from office_hero.api.schemas.dispatch import JobDispatchRequest, JobDispatchResponse
from office_hero.api.schemas.route import EmergencyDispatchRequest, RouteRead
from office_hero.core.exceptions import (
    InvalidJobTransitionError,
    JobNotFoundError,
    RouteCommitConflictError,
    SchedulingNotAvailableError,
    VehicleAlreadyBookedError,
    VehicleNotFoundError,
)
from office_hero.core.logging import get_logger

log = get_logger(__name__)

require_job_write = require_permission("job:write")
require_vehicle_read = require_permission("vehicle:read")
require_jobs_dispatch = require_permission("jobs:dispatch")
require_route_write = require_permission("route:write")


def _tenant_id(request: Request) -> UUID:
    raw = getattr(request.state, "tenant_id", None)
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return raw if isinstance(raw, UUID) else UUID(str(raw))


def _user_id(request: Request) -> UUID | None:
    raw = getattr(request.state, "user_id", None)
    if not raw:
        return None
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
            job, route_id = await service.dispatch(
                tenant_id,
                job_id,
                vehicle_id=body.vehicle_id,
                scheduled_for=body.scheduled_for,
                user_id=_user_id(request),
                travel_seconds=body.travel_seconds,
                distance_meters=body.distance_meters,
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
        except RouteCommitConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=exc.message,
            ) from exc

        return JobDispatchResponse(
            id=job.id,
            status=job.status,
            assigned_vehicle_id=cast(UUID, job.assigned_vehicle_id),
            scheduled_for=cast(datetime, job.scheduled_for),
            title=job.title,
            customer_id=job.customer_id,
            location_id=job.location_id,
            route_id=route_id,
        )

    @router.post(
        "/jobs/{job_id}/emergency-dispatch",
        response_model=RouteRead,
        status_code=status.HTTP_200_OK,
        dependencies=[Depends(require_jobs_dispatch), Depends(require_route_write)],
    )
    @limiter.limit("60/minute")
    async def emergency_dispatch(
        request: Request,
        job_id: Annotated[UUID, Path()],
        body: EmergencyDispatchRequest,
    ) -> RouteRead:
        """Drop an urgent job ahead of a vehicle's pending stops (day-of emergency)."""
        from office_hero.api.state import get_dynamic_dispatch_service

        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        service = get_dynamic_dispatch_service()

        if body.window_start is not None and body.window_end is not None:
            window_start, window_end = body.window_start, body.window_end
        else:
            today = datetime.now(UTC).date()
            window_start = datetime.combine(today, time(8, 0), tzinfo=UTC)
            window_end = datetime.combine(today, time(17, 0), tzinfo=UTC)

        try:
            route = await service.add_emergency_job(
                tenant_id,
                user_id,
                job_id,
                window_start=window_start,
                window_end=window_end,
                target_vehicle_id=body.target_vehicle_id,
            )
        except JobNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
        except VehicleNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
        except SchedulingNotAvailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message
            ) from exc
        except RouteCommitConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc

        return route

    return router
