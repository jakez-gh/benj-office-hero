"""Contract API routes — CRUD + lifecycle + due-job generation (Slice 11).

The router is built via :func:`create_contract_router` so the
:class:`~office_hero.services.contract_service.ContractService` can be injected
at app-construction time (same pattern as the job router).

RBAC summary
------------
- ``contracts:read``                  → list, get
- ``contracts:write``                 → create, update, pause, resume, end
- ``contracts:write`` + ``jobs:write`` → generate-jobs (creates Jobs)
"""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status

from office_hero.api.deps import require_permission
from office_hero.api.limiter import limiter
from office_hero.api.schemas.contract import (
    ContractCreate,
    ContractEndRequest,
    ContractList,
    ContractRead,
    ContractSummary,
    ContractUpdate,
    GenerateJobsRequest,
    GenerateJobsResponse,
)
from office_hero.api.schemas.job import JobSummary
from office_hero.core.exceptions import (
    ContractNotFoundError,
    CustomerNotFoundError,
    InvalidContractTransitionError,
    LocationNotFoundError,
)
from office_hero.core.logging import get_logger

log = get_logger(__name__)

# Module-level dependency callables — reused so tests can target them
# in ``app.dependency_overrides``.
require_contracts_read = require_permission("contracts:read")
require_contracts_write = require_permission("contracts:write")
require_jobs_write = require_permission("jobs:write")


def _tenant_id(request: Request) -> UUID:
    """Extract tenant_id from request.state; raise 401 if missing."""
    raw = getattr(request.state, "tenant_id", None)
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return raw if isinstance(raw, UUID) else UUID(str(raw))


def _user_id(request: Request) -> UUID:
    """Extract user_id from request.state for audit attribution."""
    raw = getattr(request.state, "user_id", None)
    if not raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return raw if isinstance(raw, UUID) else UUID(str(raw))


def create_contract_router(*, service_provider) -> APIRouter:
    """Construct the ``/contracts`` router with an injected service provider.

    ``service_provider`` is a zero-arg callable returning a
    :class:`~office_hero.services.contract_service.ContractService`.
    """
    router = APIRouter()

    @router.post(
        "",
        response_model=ContractRead,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_contracts_write)],
    )
    @limiter.limit("60/minute")
    async def create_contract(request: Request, body: ContractCreate) -> ContractRead:
        """Create a new contract (``contracts:write``: TenantAdmin, Sales). 60/min."""
        svc = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        try:
            contract = await svc.create(
                tenant_id,
                user_id,
                customer_id=body.customer_id,
                location_id=body.location_id,
                title=body.title,
                description=body.description,
                service_type=body.service_type,
                priority=body.priority,
                estimated_duration_min=body.estimated_duration_min,
                frequency=body.frequency.value,
                start_date=body.start_date,
                end_date=body.end_date,
                custom_fields=body.custom_fields,
            )
        except (CustomerNotFoundError, LocationNotFoundError) as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc
        return ContractRead.model_validate(contract)

    @router.get(
        "",
        response_model=ContractList,
        dependencies=[Depends(require_contracts_read)],
    )
    @limiter.limit("120/minute")
    async def list_contracts(
        request: Request,
        status_filter: Annotated[list[str] | None, Query(alias="status")] = None,
        customer_id: Annotated[UUID | None, Query()] = None,
        due_before: Annotated[date | None, Query()] = None,
        search: Annotated[str | None, Query(max_length=255)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> ContractList:
        """List contracts with optional filters (``contracts:read`` required)."""
        svc = service_provider()
        tenant_id = _tenant_id(request)
        contracts, total = await svc.list(
            tenant_id,
            status=status_filter,
            customer_id=customer_id,
            due_before=due_before,
            search=search,
            limit=limit,
            offset=offset,
        )
        items = [ContractSummary.model_validate(c) for c in contracts]
        return ContractList(items=items, total=total, limit=limit, offset=offset)

    @router.get(
        "/{contract_id}",
        response_model=ContractRead,
        dependencies=[Depends(require_contracts_read)],
    )
    async def get_contract(
        request: Request,
        contract_id: Annotated[UUID, Path()],
    ) -> ContractRead:
        """Get a single contract (``contracts:read`` required)."""
        svc = service_provider()
        tenant_id = _tenant_id(request)
        try:
            contract = await svc.get(tenant_id, contract_id)
        except ContractNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
        return ContractRead.model_validate(contract)

    @router.patch(
        "/{contract_id}",
        response_model=ContractRead,
        dependencies=[Depends(require_contracts_write)],
    )
    @limiter.limit("60/minute")
    async def update_contract(
        request: Request,
        contract_id: Annotated[UUID, Path()],
        body: ContractUpdate,
    ) -> ContractRead:
        """Apply a partial update (``contracts:write`` required)."""
        svc = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        patch = body.model_dump(exclude_unset=True)
        try:
            contract = await svc.update(tenant_id, user_id, contract_id, patch)
        except ContractNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
        except (LocationNotFoundError, CustomerNotFoundError) as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        return ContractRead.model_validate(contract)

    @router.post(
        "/{contract_id}/pause",
        response_model=ContractRead,
        dependencies=[Depends(require_contracts_write)],
    )
    async def pause_contract(
        request: Request,
        contract_id: Annotated[UUID, Path()],
    ) -> ContractRead:
        """Pause an active contract (``contracts:write`` required)."""
        svc = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        try:
            contract = await svc.pause(tenant_id, user_id, contract_id)
        except ContractNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
        except InvalidContractTransitionError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message
            ) from exc
        return ContractRead.model_validate(contract)

    @router.post(
        "/{contract_id}/resume",
        response_model=ContractRead,
        dependencies=[Depends(require_contracts_write)],
    )
    async def resume_contract(
        request: Request,
        contract_id: Annotated[UUID, Path()],
    ) -> ContractRead:
        """Resume a paused contract (``contracts:write`` required)."""
        svc = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        try:
            contract = await svc.resume(tenant_id, user_id, contract_id)
        except ContractNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
        except InvalidContractTransitionError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message
            ) from exc
        return ContractRead.model_validate(contract)

    @router.post(
        "/{contract_id}/end",
        response_model=ContractRead,
        dependencies=[Depends(require_contracts_write)],
    )
    async def end_contract(
        request: Request,
        contract_id: Annotated[UUID, Path()],
        body: ContractEndRequest | None = None,
    ) -> ContractRead:
        """End a contract — terminal (``contracts:write`` required)."""
        svc = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        try:
            contract = await svc.end(
                tenant_id, user_id, contract_id, reason=body.reason if body else None
            )
        except ContractNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
        except InvalidContractTransitionError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message
            ) from exc
        return ContractRead.model_validate(contract)

    @router.post(
        "/generate-jobs",
        response_model=GenerateJobsResponse,
        dependencies=[
            Depends(require_contracts_write),
            Depends(require_jobs_write),
        ],
    )
    @limiter.limit("10/minute")
    async def generate_jobs(
        request: Request,
        body: GenerateJobsRequest | None = None,
    ) -> GenerateJobsResponse:
        """Generate Jobs for every contract due on/before ``as_of`` (default today).

        Requires BOTH ``contracts:write`` and ``jobs:write`` since it creates
        Job rows. Designed to be hit by an admin button or a cron job.
        """
        svc = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        try:
            jobs = await svc.generate_due_jobs(
                tenant_id, user_id, as_of=body.as_of if body else None
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc
        return GenerateJobsResponse(
            generated=[JobSummary.model_validate(j) for j in jobs],
            count=len(jobs),
        )

    return router
