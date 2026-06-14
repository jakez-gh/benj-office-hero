"""Technician-facing API routes (Slice 22).

GET /vehicles/my-crew-today  — returns the caller's vehicle assignment for today.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from office_hero.api.deps import require_permission
from office_hero.api.limiter import limiter
from office_hero.api.request_context import require_tenant_id as _tenant_id
from office_hero.api.request_context import require_user_id as _user_id
from office_hero.core.logging import get_logger

log = get_logger(__name__)


class MyCrewTodayResponse(BaseModel):
    crew_id: UUID
    vehicle_id: UUID
    work_date: date


def create_tech_router(*, crew_service_provider) -> APIRouter:
    """Construct the technician router with an injected crew service provider."""
    router = APIRouter()

    @router.get(
        "/vehicles/my-crew-today",
        response_model=MyCrewTodayResponse,
        status_code=status.HTTP_200_OK,
        dependencies=[Depends(require_permission("vehicles:read"))],
    )
    @limiter.limit("60/minute")
    async def my_crew_today(request: Request) -> MyCrewTodayResponse:
        """Return the calling Technician's vehicle assignment for today.

        Uses UTC date to determine 'today'. Returns 404 if the caller has
        no crew assignment for the current date.
        """
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        today = datetime.now(UTC).date()

        svc = crew_service_provider()
        crews = await svc.list_for_user_date(tenant_id, user_id, today)
        if not crews:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No crew assignment found for today",
            )

        if len(crews) > 1:
            log.warning(
                "user.multiple_crew_assignments",
                user_id=str(user_id),
                count=len(crews),
                work_date=str(today),
            )

        crew = crews[0]
        return MyCrewTodayResponse(
            crew_id=crew.id,
            vehicle_id=crew.vehicle_id,
            work_date=today,
        )

    return router
