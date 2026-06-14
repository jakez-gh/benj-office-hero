"""Route management API routes (GET /routes, route lifecycle transitions)."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status

from office_hero.api.deps import require_permission
from office_hero.api.limiter import limiter
from office_hero.api.request_context import require_tenant_id as _tenant_id
from office_hero.api.request_context import require_user_id as _user_id
from office_hero.api.schemas.route import (
    DispatchCommitRequest,
    RouteCancelRequest,
    RouteListResponse,
    RouteRead,
    RouteReassignRequest,
    RouteReassignResponse,
    RouteResequenceRequest,
    StopSkipRequest,
)
from office_hero.core.exceptions import (
    InvalidRouteTransitionError,
    ManualSequenceInvalidError,
    RouteCommitConflictError,
    RouteNotFoundError,
    VehicleNotFoundError,
)
from office_hero.core.logging import get_logger

log = get_logger(__name__)


def create_routes_router(*, service_provider, repo_provider) -> APIRouter:
    """Construct the routes router with injected providers."""
    router = APIRouter(prefix="/routes", tags=["routes"])

    @router.get(
        "",
        response_model=RouteListResponse,
        dependencies=[Depends(require_permission("route:read"))],
    )
    @limiter.limit("60/minute")
    async def list_routes(
        request: Request,
        date_param: Annotated[date, Query(alias="date", description="ISO date (required)")] = ...,
        vehicle_id: Annotated[UUID | None, Query()] = None,
        status: Annotated[list[str] | None, Query()] = None,
    ) -> RouteListResponse:
        """List routes for a given date with optional filters."""
        tenant_id = _tenant_id(request)
        repo = repo_provider()

        routes = await repo.list_for_date(
            tenant_id,
            date_param,
            vehicle_id=vehicle_id,
            status=status,
        )

        return RouteListResponse(items=routes, total=len(routes))

    @router.get(
        "/{route_id}",
        response_model=RouteRead,
        dependencies=[Depends(require_permission("route:read"))],
    )
    @limiter.limit("60/minute")
    async def get_route(
        request: Request,
        route_id: Annotated[UUID, Path()],
    ) -> RouteRead:
        """Get a single route by ID."""
        tenant_id = _tenant_id(request)
        repo = repo_provider()

        route = await repo.get_by_id(route_id, tenant_id)
        if not route:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")

        return route

    @router.post(
        "", response_model=RouteRead, dependencies=[Depends(require_permission("route:write"))]
    )
    @limiter.limit("60/minute")
    async def commit_dispatch(
        request: Request,
        job_id: Annotated[UUID, Query(description="Job ID to dispatch")],
        body: DispatchCommitRequest,
    ) -> RouteRead:
        """Create a route by committing a dispatch (option or manual sequence)."""
        from office_hero.api.state import get_dispatch_service
        from office_hero.services.dispatch_service import DispatchCommitPayload

        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        service = get_dispatch_service()

        try:
            payload = DispatchCommitPayload(
                date=body.date,
                option_kind=body.option_kind,
                manual_vehicle_id=body.manual_vehicle_id,
                manual_sequence=body.manual_sequence,
                notes=body.notes,
            )
            route = await service.commit_dispatch(
                tenant_id, user_id, job_id=job_id, payload=payload
            )
        except RouteCommitConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc
        except ManualSequenceInvalidError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        return route

    @router.post(
        "/{route_id}/resequence",
        response_model=RouteRead,
        dependencies=[Depends(require_permission("route:write"))],
    )
    @limiter.limit("60/minute")
    async def resequence_route(
        request: Request,
        route_id: Annotated[UUID, Path()],
        body: RouteResequenceRequest,
    ) -> RouteRead:
        """Reorder a committed route's stops — the manual sequence override."""
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        service = service_provider()

        try:
            route = await service.resequence_route(
                tenant_id, user_id, route_id, job_ids=body.job_ids
            )
        except RouteNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidRouteTransitionError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc
        except ManualSequenceInvalidError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc

        return route

    @router.post(
        "/{route_id}/reassign",
        response_model=RouteReassignResponse,
        dependencies=[Depends(require_permission("route:write"))],
    )
    @limiter.limit("60/minute")
    async def reassign_route(
        request: Request,
        route_id: Annotated[UUID, Path()],
        body: RouteReassignRequest,
    ) -> RouteReassignResponse:
        """Reassign a route's pending stops to another vehicle (day-of, e.g. tech sick)."""
        from office_hero.api.state import get_dynamic_dispatch_service

        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        service = get_dynamic_dispatch_service()

        try:
            result = await service.reassign_route(
                tenant_id, user_id, route_id, target_vehicle_id=body.target_vehicle_id
            )
        except RouteNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except VehicleNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except RouteCommitConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

        return RouteReassignResponse(
            source_route=result["source_route"],
            target_route=result["target_route"],
            moved_count=result["moved_count"],
        )

    @router.post(
        "/{route_id}/start",
        response_model=RouteRead,
        dependencies=[Depends(require_permission("route:write"))],
    )
    @limiter.limit("60/minute")
    async def start_route(
        request: Request,
        route_id: Annotated[UUID, Path()],
    ) -> RouteRead:
        """Transition a route from committed to in_progress."""
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        service = service_provider()

        try:
            route = await service.start_route(tenant_id, user_id, route_id)
        except RouteNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidRouteTransitionError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc

        return route

    @router.post(
        "/{route_id}/cancel",
        response_model=RouteRead,
        dependencies=[Depends(require_permission("route:write"))],
    )
    @limiter.limit("60/minute")
    async def cancel_route(
        request: Request,
        route_id: Annotated[UUID, Path()],
        body: RouteCancelRequest,
    ) -> RouteRead:
        """Cancel a route and revert scheduled jobs to pending."""
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        service = service_provider()

        try:
            route = await service.cancel_route(tenant_id, user_id, route_id, reason=body.reason)
        except RouteNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidRouteTransitionError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc

        return route

    @router.post(
        "/{route_id}/stops/{stop_id}/arrived",
        response_model=RouteRead,
        dependencies=[Depends(require_permission("route:write"))],
    )
    @limiter.limit("60/minute")
    async def mark_stop_arrived(
        request: Request,
        route_id: Annotated[UUID, Path()],
        stop_id: Annotated[UUID, Path()],
    ) -> RouteRead:
        """Mark a route stop as arrived."""
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        service = service_provider()
        repo = repo_provider()

        await service.mark_stop_arrived(tenant_id, user_id, stop_id)
        route = await repo.get_by_id(route_id, tenant_id)
        if not route:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
        return route

    @router.post(
        "/{route_id}/stops/{stop_id}/complete",
        response_model=RouteRead,
        dependencies=[Depends(require_permission("route:write"))],
    )
    @limiter.limit("60/minute")
    async def mark_stop_complete(
        request: Request,
        route_id: Annotated[UUID, Path()],
        stop_id: Annotated[UUID, Path()],
    ) -> RouteRead:
        """Mark a route stop as complete."""
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        service = service_provider()
        repo = repo_provider()

        await service.mark_stop_complete(tenant_id, user_id, stop_id)
        route = await repo.get_by_id(route_id, tenant_id)
        if not route:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
        return route

    @router.post(
        "/{route_id}/stops/{stop_id}/skip",
        response_model=RouteRead,
        dependencies=[Depends(require_permission("route:write"))],
    )
    @limiter.limit("60/minute")
    async def skip_stop(
        request: Request,
        route_id: Annotated[UUID, Path()],
        stop_id: Annotated[UUID, Path()],
        body: StopSkipRequest,
    ) -> RouteRead:
        """Skip a route stop and optionally auto-complete route if all terminal."""
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        service = service_provider()
        repo = repo_provider()

        await service.mark_stop_skipped(tenant_id, user_id, stop_id, body.reason)
        route = await repo.get_by_id(route_id, tenant_id)
        if not route:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found")
        return route

    return router
