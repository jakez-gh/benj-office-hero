"""Vehicle location API route — PUT /vehicles/{vehicle_id}/location (Slice 15)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status

from office_hero.api.deps import require_permission
from office_hero.api.limiter import limiter
from office_hero.api.schemas.vehicle_location import (
    VehicleLocationRequest,
    VehicleLocationResponse,
)
from office_hero.core.exceptions import VehicleNotFoundError


def _tenant_id(request: Request) -> UUID:
    raw = getattr(request.state, "tenant_id", None)
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return raw if isinstance(raw, UUID) else UUID(str(raw))


def create_vehicle_location_router(*, service_provider) -> APIRouter:
    router = APIRouter()

    @router.put(
        "/vehicles/{vehicle_id}/location",
        response_model=VehicleLocationResponse,
        status_code=status.HTTP_200_OK,
        dependencies=[Depends(require_permission("vehicle:write"))],
    )
    @limiter.limit("120/minute")
    async def record_location(
        request: Request,
        vehicle_id: Annotated[UUID, Path()],
        body: VehicleLocationRequest,
    ) -> VehicleLocationResponse:
        """Record a GPS fix for a vehicle (120/min — GPS polling rate)."""
        tenant_id = _tenant_id(request)
        svc = service_provider()
        try:
            fix = await svc.record(
                tenant_id,
                vehicle_id,
                lat=body.lat,
                lng=body.lng,
                accuracy_m=body.accuracy_m,
                recorded_at=body.recorded_at,
            )
        except VehicleNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=exc.message,
            ) from exc

        return VehicleLocationResponse(
            id=fix.id,
            vehicle_id=fix.vehicle_id,
            lat=fix.lat,
            lng=fix.lng,
            accuracy_m=fix.accuracy_m,
            recorded_at=fix.recorded_at,
        )

    @router.get(
        "/vehicles/{vehicle_id}/location",
        response_model=VehicleLocationResponse,
        dependencies=[Depends(require_permission("vehicle:read"))],
    )
    @limiter.limit("120/minute")
    async def get_latest_location(
        request: Request,
        vehicle_id: Annotated[UUID, Path()],
    ) -> VehicleLocationResponse:
        """Return the most recent GPS fix for a vehicle (404 when none recorded)."""
        tenant_id = _tenant_id(request)
        svc = service_provider()
        fix = await svc.get_latest(tenant_id, vehicle_id)
        if fix is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No location recorded for this vehicle",
            )

        return VehicleLocationResponse(
            id=fix.id,
            vehicle_id=fix.vehicle_id,
            lat=fix.lat,
            lng=fix.lng,
            accuracy_m=fix.accuracy_m,
            recorded_at=fix.recorded_at,
        )

    return router
