"""Vehicle API routes — CRUD + archive/restore with RBAC and rate limiting.

Write operations (create, patch, archive, restore) are restricted to
TenantAdmin, Operator, and OperatorStaff. Dispatchers can read but not write.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status

from office_hero.api.deps import require_permission, require_role
from office_hero.api.limiter import limiter
from office_hero.api.schemas.vehicle import (
    VehicleCreate,
    VehicleList,
    VehicleRead,
    VehicleSummary,
    VehicleUpdate,
)
from office_hero.core.exceptions import (
    CrewAssignmentConflictError,
    VehicleNotFoundError,
)
from office_hero.core.logging import get_logger
from office_hero.core.roles import Role

log = get_logger(__name__)

require_vehicles_read = require_permission("vehicles:read")
require_vehicles_write = require_role([Role.TenantAdmin, Role.Operator, Role.OperatorStaff])


def _tenant_id(request: Request) -> UUID:
    raw = getattr(request.state, "tenant_id", None)
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return raw if isinstance(raw, UUID) else UUID(str(raw))


def _user_id(request: Request) -> UUID:
    raw = getattr(request.state, "user_id", None)
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return raw if isinstance(raw, UUID) else UUID(str(raw))


def create_vehicle_router(*, service_provider) -> APIRouter:
    """Construct the ``/vehicles`` router with an injected service provider."""
    router = APIRouter()

    @router.post(
        "",
        response_model=VehicleRead,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_vehicles_write)],
    )
    @limiter.limit("60/minute")
    async def create_vehicle(request: Request, body: VehicleCreate) -> VehicleRead:
        """Create a vehicle (admin/operator only)."""
        service = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        v = await service.create(
            tenant_id,
            user_id,
            license_plate=body.license_plate,
            nickname=body.nickname,
            make=body.make,
            model=body.model,
            year=body.year,
            vin=body.vin,
            gps_device_id=body.gps_device_id,
            capacity_kg=body.capacity_kg,
            home_base_lat=body.home_base_lat,
            home_base_lng=body.home_base_lng,
            notes=body.notes,
        )
        return VehicleRead.model_validate(v)

    @router.get(
        "",
        response_model=VehicleList,
        dependencies=[Depends(require_vehicles_read)],
    )
    @limiter.limit("120/minute")
    async def list_vehicles(
        request: Request,
        search: Annotated[str | None, Query(max_length=255)] = None,
        archived: Annotated[bool, Query()] = False,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> VehicleList:
        """List vehicles (paginated)."""
        service = service_provider()
        tenant_id = _tenant_id(request)
        rows, total = await service.list(
            tenant_id, archived=archived, search=search, limit=limit, offset=offset
        )
        items = [VehicleSummary.model_validate(v) for v in rows]
        return VehicleList(items=items, total=total, limit=limit, offset=offset)

    @router.get(
        "/{vehicle_id}",
        response_model=VehicleRead,
        dependencies=[Depends(require_vehicles_read)],
    )
    async def get_vehicle(
        request: Request,
        vehicle_id: Annotated[UUID, Path()],
    ) -> VehicleRead:
        """Get a vehicle by ID."""
        service = service_provider()
        tenant_id = _tenant_id(request)
        try:
            v = await service.get(tenant_id, vehicle_id)
        except VehicleNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return VehicleRead.model_validate(v)

    @router.patch(
        "/{vehicle_id}",
        response_model=VehicleRead,
        dependencies=[Depends(require_vehicles_write)],
    )
    @limiter.limit("60/minute")
    async def update_vehicle(
        request: Request,
        vehicle_id: Annotated[UUID, Path()],
        body: VehicleUpdate,
    ) -> VehicleRead:
        """Apply a partial update."""
        service = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        patch: dict[str, Any] = body.model_dump(exclude_unset=True)
        try:
            v = await service.update(tenant_id, user_id, vehicle_id, patch)
        except VehicleNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return VehicleRead.model_validate(v)

    @router.post(
        "/{vehicle_id}/archive",
        response_model=VehicleRead,
        dependencies=[Depends(require_vehicles_write)],
    )
    @limiter.limit("60/minute")
    async def archive_vehicle(
        request: Request,
        vehicle_id: Annotated[UUID, Path()],
    ) -> VehicleRead:
        """Soft-delete a vehicle; 409 if active/future crews exist."""
        service = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        try:
            v = await service.archive(tenant_id, user_id, vehicle_id)
        except VehicleNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except CrewAssignmentConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "detail": exc.message,
                    "existing_crew_id": str(exc.existing_crew_id) if exc.existing_crew_id else None,
                },
            ) from exc
        return VehicleRead.model_validate(v)

    @router.post(
        "/{vehicle_id}/restore",
        response_model=VehicleRead,
        dependencies=[Depends(require_vehicles_write)],
    )
    @limiter.limit("60/minute")
    async def restore_vehicle(
        request: Request,
        vehicle_id: Annotated[UUID, Path()],
    ) -> VehicleRead:
        """Restore an archived vehicle."""
        service = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        try:
            v = await service.restore(tenant_id, user_id, vehicle_id)
        except VehicleNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return VehicleRead.model_validate(v)

    return router
