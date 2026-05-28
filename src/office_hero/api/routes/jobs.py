"""Job API routes — CRUD + status lifecycle, with RBAC and rate limiting.

The router is built via :func:`create_job_router` so the
:class:`~office_hero.services.job_service.JobService` can be injected at
app-construction time (same pattern as the customer router).

RBAC summary
------------
- ``jobs:read``      → list, get
- ``jobs:write``     → create, update
- ``jobs:dispatch``  → schedule, cancel
- Role-based         → start (Technician/TechnicianHelper/Dispatcher/TenantAdmin/Operator/OperatorStaff)
- Role-based         → complete (same set)
"""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status

from office_hero.api.deps import require_permission, require_role
from office_hero.api.limiter import limiter
from office_hero.api.schemas.job import (
    JobCancelRequest,
    JobCompleteRequest,
    JobCreate,
    JobList,
    JobRead,
    JobScheduleRequest,
    JobSummary,
    JobUpdate,
)
from office_hero.core.exceptions import (
    CustomerNotFoundError,
    JobNotFoundError,
    LocationNotFoundError,
)
from office_hero.core.logging import get_logger
from office_hero.core.roles import Role

log = get_logger(__name__)

# Module-level dependency callables — reused so tests can target them
# in ``app.dependency_overrides``.
require_jobs_read = require_permission("jobs:read")
require_jobs_write = require_permission("jobs:write")
require_jobs_dispatch = require_permission("jobs:dispatch")
require_jobs_cancel = require_permission("jobs:cancel")

# Roles allowed to start / complete a job (field-side actions).
_FIELD_ROLES = [
    Role.Technician,
    Role.TechnicianHelper,
    Role.Dispatcher,
    Role.TenantAdmin,
    Role.Operator,
    Role.OperatorStaff,
]
require_field_role = require_role(_FIELD_ROLES)


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


def create_job_router(*, service_provider) -> APIRouter:
    """Construct the ``/jobs`` router with an injected service provider.

    ``service_provider`` is a zero-arg callable returning a
    :class:`~office_hero.services.job_service.JobService` (per-request).
    """
    router = APIRouter()

    @router.post(
        "",
        response_model=JobRead,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_jobs_write)],
    )
    @limiter.limit("60/minute")
    async def create_job(request: Request, body: JobCreate) -> JobRead:
        """Create a new job (``jobs:write`` required). Rate-limited at 60/min."""
        svc = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        try:
            job = await svc.create(
                tenant_id,
                user_id,
                customer_id=body.customer_id,
                location_id=body.location_id,
                title=body.title,
                description=body.description,
                priority=body.priority,
                service_type=body.service_type,
                requested_at=body.requested_at,
                requested_until=body.requested_until,
                estimated_duration_min=body.estimated_duration_min,
                custom_fields=body.custom_fields,
            )
        except (CustomerNotFoundError, LocationNotFoundError) as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
        return JobRead.model_validate(job)

    @router.get(
        "",
        response_model=JobList,
        dependencies=[Depends(require_jobs_read)],
    )
    @limiter.limit("120/minute")
    async def list_jobs(
        request: Request,
        status_filter: Annotated[list[str] | None, Query(alias="status")] = None,
        customer_id: Annotated[UUID | None, Query()] = None,
        scheduled_for_date: Annotated[date | None, Query()] = None,
        search: Annotated[str | None, Query(max_length=255)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> JobList:
        """List jobs with optional filters (``jobs:read`` required)."""
        svc = service_provider()
        tenant_id = _tenant_id(request)
        jobs, total = await svc.list(
            tenant_id,
            status=status_filter,
            customer_id=customer_id,
            scheduled_for_date=scheduled_for_date,
            search=search,
            limit=limit,
            offset=offset,
        )
        items = [JobSummary.model_validate(j) for j in jobs]
        return JobList(items=items, total=total, limit=limit, offset=offset)

    @router.get(
        "/{job_id}",
        response_model=JobRead,
        dependencies=[Depends(require_jobs_read)],
    )
    async def get_job(
        request: Request,
        job_id: Annotated[UUID, Path()],
    ) -> JobRead:
        """Get a single job (``jobs:read`` required)."""
        svc = service_provider()
        tenant_id = _tenant_id(request)
        try:
            job = await svc.get(tenant_id, job_id)
        except JobNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
        return JobRead.model_validate(job)

    @router.patch(
        "/{job_id}",
        response_model=JobRead,
        dependencies=[Depends(require_jobs_write)],
    )
    @limiter.limit("60/minute")
    async def update_job(
        request: Request,
        job_id: Annotated[UUID, Path()],
        body: JobUpdate,
    ) -> JobRead:
        """Apply a partial update (``jobs:write`` required)."""
        svc = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        patch = body.model_dump(exclude_unset=True)
        try:
            job = await svc.update(tenant_id, user_id, job_id, patch)
        except JobNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
        except (LocationNotFoundError, CustomerNotFoundError) as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        return JobRead.model_validate(job)

    @router.post(
        "/{job_id}/schedule",
        response_model=JobRead,
        dependencies=[Depends(require_jobs_dispatch)],
    )
    async def schedule_job(
        request: Request,
        job_id: Annotated[UUID, Path()],
        body: JobScheduleRequest,
    ) -> JobRead:
        """Schedule a job (``jobs:dispatch`` required: Dispatcher, TenantAdmin, Operator)."""
        svc = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        try:
            job = await svc.schedule(tenant_id, user_id, job_id, body.scheduled_for)
        except JobNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
        return JobRead.model_validate(job)

    @router.post(
        "/{job_id}/start",
        response_model=JobRead,
        dependencies=[Depends(require_field_role)],
    )
    async def start_job(
        request: Request,
        job_id: Annotated[UUID, Path()],
    ) -> JobRead:
        """Start a job (field roles: Technician/TechnicianHelper/Dispatcher/TenantAdmin/Operator/OperatorStaff)."""
        svc = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        try:
            job = await svc.start(tenant_id, user_id, job_id)
        except JobNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
        return JobRead.model_validate(job)

    @router.post(
        "/{job_id}/complete",
        response_model=JobRead,
        dependencies=[Depends(require_field_role)],
    )
    async def complete_job(
        request: Request,
        job_id: Annotated[UUID, Path()],
        body: JobCompleteRequest,
    ) -> JobRead:
        """Complete a job (field roles required)."""
        svc = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        try:
            job = await svc.complete(
                tenant_id, user_id, job_id, completion_notes=body.completion_notes
            )
        except JobNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
        return JobRead.model_validate(job)

    @router.post(
        "/{job_id}/cancel",
        response_model=JobRead,
        dependencies=[Depends(require_jobs_cancel)],
    )
    async def cancel_job(
        request: Request,
        job_id: Annotated[UUID, Path()],
        body: JobCancelRequest,
    ) -> JobRead:
        """Cancel a job (``jobs:cancel`` required: Dispatcher, TenantAdmin, Operator)."""
        svc = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        try:
            job = await svc.cancel(tenant_id, user_id, job_id, reason=body.reason)
        except JobNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
        return JobRead.model_validate(job)

    return router
