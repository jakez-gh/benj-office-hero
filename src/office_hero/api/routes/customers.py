"""Customer API routes — CRUD + archive/restore, with RBAC and audit emission.

The router is built via :func:`create_customer_router` so the
:class:`CustomerService` can be injected at app construction time. Tenant
isolation relies on ``request.state.tenant_id`` set by the JWT middleware
(slice 3) and re-checked at the repository / RLS layers.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status

from office_hero.api.deps import require_permission, require_role
from office_hero.api.limiter import limiter
from office_hero.api.request_context import require_tenant_id as _tenant_id
from office_hero.api.request_context import require_user_id as _user_id
from office_hero.api.schemas.customer import (
    CustomerCreate,
    CustomerList,
    CustomerRead,
    CustomerSummary,
    CustomerUpdate,
)
from office_hero.api.schemas.location import LocationRead
from office_hero.core.exceptions import CustomerNotFoundError, DuplicateEmailError
from office_hero.core.logging import get_logger
from office_hero.core.roles import Role

log = get_logger(__name__)

# Module-level dependency callables. Reused across endpoints so tests can swap
# them via ``app.dependency_overrides``.
require_customers_read = require_permission("customers:read")
require_customers_write = require_permission("customers:write")
require_customer_admin = require_role([Role.TenantAdmin, Role.Operator, Role.OperatorStaff])


def create_customer_router(
    *,
    service_provider,
    location_service_provider=None,
) -> APIRouter:
    """Construct the ``/customers`` router with injected service providers.

    ``service_provider`` is a zero-arg callable returning a
    :class:`CustomerService` (per-request). Letting the factory hold a
    closure rather than the service directly mirrors the pattern used by
    ``create_admin_router`` and keeps the service per-request when wiring a
    real DB session later.
    """
    router = APIRouter()

    @router.post(
        "",
        response_model=CustomerRead,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_customers_write)],
    )
    @limiter.limit("60/minute")
    async def create_customer(
        request: Request,
        body: CustomerCreate,
    ) -> CustomerRead:
        """Create a customer (write permission required)."""
        service = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        try:
            cust = await service.create(
                tenant_id=tenant_id,
                user_id=user_id,
                name=body.name,
                email=body.email,
                phone=body.phone,
                notes=body.notes,
            )
        except DuplicateEmailError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=exc.message,
            ) from exc
        return CustomerRead.model_validate(cust)

    @router.get(
        "",
        response_model=CustomerList,
        dependencies=[Depends(require_customers_read)],
    )
    async def list_customers(
        request: Request,
        search: Annotated[str | None, Query(max_length=255)] = None,
        archived: Annotated[bool, Query()] = False,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> CustomerList:
        """List customers (paginated, optionally substring-filtered)."""
        service = service_provider()
        tenant_id = _tenant_id(request)
        rows, total = await service.list_summaries(
            tenant_id,
            search=search,
            archived=archived,
            limit=limit,
            offset=offset,
        )
        items = [
            CustomerSummary(
                id=r.id,
                name=r.name,
                archived=r.archived,
                location_count=location_count,
                primary_city=primary_city,
            )
            for r, location_count, primary_city in rows
        ]
        return CustomerList(items=items, total=total, limit=limit, offset=offset)

    @router.get(
        "/{customer_id}",
        response_model=CustomerRead,
        dependencies=[Depends(require_customers_read)],
    )
    async def get_customer(
        request: Request,
        customer_id: Annotated[UUID, Path()],
    ) -> CustomerRead:
        """Get a customer, including embedded locations."""
        service = service_provider()
        tenant_id = _tenant_id(request)
        try:
            cust = await service.get(tenant_id, customer_id)
        except CustomerNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

        locations: list[LocationRead] = []
        if location_service_provider is not None:
            loc_service = location_service_provider()
            locs = await loc_service.list_for_customer(tenant_id, customer_id)
            locations = [LocationRead.model_validate(loc) for loc in locs]

        read = CustomerRead.model_validate(cust)
        # Pydantic v2: model_copy avoids losing extra fields when ``locations``
        # was originally an empty list from the ORM attribute.
        return read.model_copy(update={"locations": locations})

    @router.patch(
        "/{customer_id}",
        response_model=CustomerRead,
        dependencies=[Depends(require_customers_write)],
    )
    async def update_customer(
        request: Request,
        customer_id: Annotated[UUID, Path()],
        body: CustomerUpdate,
    ) -> CustomerRead:
        """Apply a partial update."""
        service = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        patch: dict[str, Any] = body.model_dump(exclude_unset=True)
        try:
            cust = await service.update(tenant_id, user_id, customer_id, patch)
        except CustomerNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return CustomerRead.model_validate(cust)

    @router.post(
        "/{customer_id}/archive",
        response_model=CustomerRead,
        dependencies=[Depends(require_customer_admin)],
    )
    async def archive_customer(
        request: Request,
        customer_id: Annotated[UUID, Path()],
    ) -> CustomerRead:
        """Soft-delete a customer (admin only)."""
        service = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        try:
            cust = await service.archive(tenant_id, user_id, customer_id)
        except CustomerNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return CustomerRead.model_validate(cust)

    @router.post(
        "/{customer_id}/restore",
        response_model=CustomerRead,
        dependencies=[Depends(require_customer_admin)],
    )
    async def restore_customer(
        request: Request,
        customer_id: Annotated[UUID, Path()],
    ) -> CustomerRead:
        """Clear the archived flag (admin only)."""
        service = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        try:
            cust = await service.restore(tenant_id, user_id, customer_id)
        except CustomerNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return CustomerRead.model_validate(cust)

    return router
