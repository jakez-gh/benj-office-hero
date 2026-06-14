"""Location API routes — CRUD + geocoding controls under a Customer parent."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status

from office_hero.api.deps import require_permission, require_role
from office_hero.api.limiter import limiter
from office_hero.api.request_context import require_tenant_id as _tenant_id
from office_hero.api.request_context import require_user_id as _user_id
from office_hero.api.schemas.location import (
    LocationCoordinatesSet,
    LocationCreate,
    LocationRead,
    LocationUpdate,
)
from office_hero.core.exceptions import (
    CustomerNotFoundError,
    LocationNotFoundError,
)
from office_hero.core.logging import get_logger
from office_hero.core.roles import Role
from office_hero.services.location_service import LocationService

log = get_logger(__name__)


require_customers_read = require_permission("customers:read")
require_customers_write = require_permission("customers:write")
require_dispatch_or_admin = require_role([Role.Dispatcher, Role.TenantAdmin, Role.Operator])
require_archive_role = require_role([Role.TenantAdmin, Role.Operator, Role.OperatorStaff])


def create_location_router(*, service_provider) -> APIRouter:
    """Construct the locations router. See ``create_customer_router``."""
    router = APIRouter()

    @router.post(
        "/customers/{customer_id}/locations",
        response_model=LocationRead,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_customers_write)],
    )
    @limiter.limit("60/minute")
    async def create_location(
        request: Request,
        customer_id: Annotated[UUID, Path()],
        body: LocationCreate,
    ) -> LocationRead:
        """Create a location under ``customer_id`` and (optionally) geocode it."""
        service: LocationService = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)

        address_fields = {
            "street": body.street,
            "street2": body.street2,
            "city": body.city,
            "state": body.state,
            "postal_code": body.postal_code,
            "country": body.country,
        }
        try:
            loc = await service.create(
                tenant_id=tenant_id,
                user_id=user_id,
                customer_id=customer_id,
                address_fields=address_fields,
                label=body.label,
                geocode=body.geocode,
            )
        except CustomerNotFoundError as exc:
            # Surface as 404 so cross-tenant attempts get the standard
            # silent-isolation behaviour.
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

        return LocationRead.model_validate(loc)

    @router.get(
        "/customers/{customer_id}/locations",
        response_model=list[LocationRead],
        dependencies=[Depends(require_customers_read)],
    )
    async def list_locations(
        request: Request,
        customer_id: Annotated[UUID, Path()],
    ) -> list[LocationRead]:
        """List a customer's locations."""
        service: LocationService = service_provider()
        tenant_id = _tenant_id(request)
        try:
            locs = await service.list_for_customer(tenant_id, customer_id)
        except CustomerNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return [LocationRead.model_validate(loc) for loc in locs]

    @router.get(
        "/locations/{location_id}",
        response_model=LocationRead,
        dependencies=[Depends(require_customers_read)],
    )
    async def get_location(
        request: Request,
        location_id: Annotated[UUID, Path()],
    ) -> LocationRead:
        """Get a single location by id (tenant-scoped)."""
        service: LocationService = service_provider()
        tenant_id = _tenant_id(request)
        try:
            loc = await service.get(tenant_id, location_id)
        except LocationNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return LocationRead.model_validate(loc)

    @router.patch(
        "/locations/{location_id}",
        response_model=LocationRead,
        dependencies=[Depends(require_customers_write)],
    )
    async def update_location(
        request: Request,
        location_id: Annotated[UUID, Path()],
        body: LocationUpdate,
    ) -> LocationRead:
        """Update a location; may auto re-geocode on address change."""
        service: LocationService = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)

        data: dict[str, Any] = body.model_dump(exclude_unset=True)
        regeocode = data.pop("regeocode", "auto")
        try:
            loc = await service.update(tenant_id, user_id, location_id, data, regeocode=regeocode)
        except LocationNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return LocationRead.model_validate(loc)

    @router.post(
        "/locations/{location_id}/coordinates",
        response_model=LocationRead,
        dependencies=[Depends(require_dispatch_or_admin)],
    )
    async def set_coordinates(
        request: Request,
        location_id: Annotated[UUID, Path()],
        body: LocationCoordinatesSet,
    ) -> LocationRead:
        """Manual coordinate override (Dispatcher/Admin/Operator only)."""
        service: LocationService = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        try:
            loc = await service.manual_set_coordinates(
                tenant_id, user_id, location_id, body.lat, body.lng
            )
        except LocationNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return LocationRead.model_validate(loc)

    @router.post(
        "/locations/{location_id}/regeocode",
        response_model=LocationRead,
        dependencies=[Depends(require_dispatch_or_admin)],
    )
    @limiter.limit("5/minute")
    async def regeocode_location(
        request: Request,
        location_id: Annotated[UUID, Path()],
    ) -> LocationRead:
        """Force a re-geocode (rate-limited to protect Nominatim quota)."""
        service: LocationService = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        try:
            loc = await service.regeocode(tenant_id, user_id, location_id)
        except LocationNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return LocationRead.model_validate(loc)

    @router.post(
        "/locations/{location_id}/archive",
        response_model=LocationRead,
        dependencies=[Depends(require_archive_role)],
    )
    async def archive_location(
        request: Request,
        location_id: Annotated[UUID, Path()],
    ) -> LocationRead:
        """Soft-delete a location (admin only)."""
        service: LocationService = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        try:
            loc = await service.archive(tenant_id, user_id, location_id)
        except LocationNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return LocationRead.model_validate(loc)

    return router
