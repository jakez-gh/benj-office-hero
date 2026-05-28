"""VehicleCrew API routes — CRUD with RBAC and rate limiting.

Crew creation/mutation requires Dispatcher, TenantAdmin, Operator, or
OperatorStaff. Technicians can list/read only their own crews. Conflicts
endpoint is Dispatcher+admin only.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status

from office_hero.api.deps import require_role
from office_hero.api.limiter import limiter
from office_hero.api.schemas.vehicle_crew import (
    CrewConflictRead,
    CrewMemberRead,
    VehicleCrewCreate,
    VehicleCrewList,
    VehicleCrewMembersReplace,
    VehicleCrewRead,
    VehicleCrewUpdate,
)
from office_hero.api.schemas.vehicle_crew import (
    CrewMemberInput as SchemaCrewMemberInput,
)
from office_hero.core.exceptions import (
    CrewAssignmentConflictError,
    InvalidCrewMemberError,
    VehicleCrewNotFoundError,
    VehicleNotFoundError,
)
from office_hero.core.logging import get_logger
from office_hero.core.roles import Role
from office_hero.repositories.vehicle_crew_repository import (
    CrewMemberInput as RepoCMI,
)

log = get_logger(__name__)

_CREW_WRITE_ROLES = [Role.Dispatcher, Role.TenantAdmin, Role.Operator, Role.OperatorStaff]
_CREW_READ_ROLES = [
    Role.Dispatcher,
    Role.TenantAdmin,
    Role.Operator,
    Role.OperatorStaff,
    Role.Technician,
    Role.TechnicianHelper,
]
_CREW_CONFLICT_ROLES = [Role.Dispatcher, Role.TenantAdmin, Role.Operator, Role.OperatorStaff]

require_crew_write = require_role(_CREW_WRITE_ROLES)
require_crew_read = require_role(_CREW_READ_ROLES)
require_crew_conflict_read = require_role(_CREW_CONFLICT_ROLES)


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


def _role(request: Request) -> str:
    return getattr(request.state, "role", "")


def _schema_to_repo_member(m: SchemaCrewMemberInput) -> RepoCMI:
    return RepoCMI(user_id=m.user_id, role_on_crew=m.role_on_crew)


def create_vehicle_crew_router(*, service_provider, vehicle_service_provider=None) -> APIRouter:
    """Construct the ``/vehicle-crews`` router with injected service providers."""
    router = APIRouter()

    @router.post(
        "/vehicle-crews",
        response_model=VehicleCrewRead,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_crew_write)],
    )
    @limiter.limit("60/minute")
    async def create_crew(request: Request, body: VehicleCrewCreate) -> VehicleCrewRead:
        """Create a date-scoped vehicle crew."""
        service = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        members = [_schema_to_repo_member(m) for m in body.members]
        try:
            crew = await service.create(
                tenant_id,
                user_id,
                vehicle_id=body.vehicle_id,
                work_date=body.work_date,
                shift_start=body.shift_start,
                shift_end=body.shift_end,
                notes=body.notes,
                members=members,
            )
        except VehicleNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except CrewAssignmentConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "detail": exc.message,
                    "existing_crew_id": (
                        str(exc.existing_crew_id) if exc.existing_crew_id else None
                    ),
                },
            ) from exc
        except InvalidCrewMemberError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "detail": exc.message,
                    "user_id": str(exc.user_id) if exc.user_id else None,
                    "reason": exc.reason,
                },
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc
        return _to_crew_read(crew)

    @router.get(
        "/vehicle-crews",
        response_model=VehicleCrewList,
        dependencies=[Depends(require_crew_read)],
    )
    @limiter.limit("120/minute")
    async def list_crews(
        request: Request,
        work_date: Annotated[date, Query()],
        vehicle_id: Annotated[UUID | None, Query()] = None,
    ) -> VehicleCrewList:
        """List crews for a date. Technicians see only their own crews."""
        service = service_provider()
        tenant_id = _tenant_id(request)
        user_id_state = _user_id(request)
        role = _role(request)

        crews = await service.list_for_date(tenant_id, work_date)

        if vehicle_id is not None:
            crews = [c for c in crews if c.vehicle_id == vehicle_id]

        # Technician/TechnicianHelper: restrict to their own crews
        if role in (Role.Technician.value, Role.TechnicianHelper.value):
            crews = [c for c in crews if any(m.user_id == user_id_state for m in (c.members or []))]

        return VehicleCrewList(
            items=[_to_crew_read(c) for c in crews],
            total=len(crews),
        )

    @router.get(
        "/vehicle-crews/conflicts",
        response_model=list[CrewConflictRead],
        dependencies=[Depends(require_crew_conflict_read)],
    )
    @limiter.limit("120/minute")
    async def get_conflicts(
        request: Request,
        work_date: Annotated[date, Query()],
    ) -> list[CrewConflictRead]:
        """Return double-booked users for the given date."""
        service = service_provider()
        tenant_id = _tenant_id(request)
        conflicts = await service.conflicts_for_date(tenant_id, work_date)
        return [
            CrewConflictRead(user_id=uid, crew_ids=crew_ids, work_date=work_date)
            for uid, crew_ids in conflicts
        ]

    @router.get(
        "/vehicle-crews/{crew_id}",
        response_model=VehicleCrewRead,
        dependencies=[Depends(require_crew_read)],
    )
    async def get_crew(
        request: Request,
        crew_id: Annotated[UUID, Path()],
    ) -> VehicleCrewRead:
        """Get a crew. Technicians can only read crews they are on."""
        service = service_provider()
        tenant_id = _tenant_id(request)
        user_id_state = _user_id(request)
        role = _role(request)
        try:
            crew = await service.get(tenant_id, crew_id)
        except VehicleCrewNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

        if role in (Role.Technician.value, Role.TechnicianHelper.value) and not any(
            m.user_id == user_id_state for m in (crew.members or [])
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        return _to_crew_read(crew)

    @router.patch(
        "/vehicle-crews/{crew_id}",
        response_model=VehicleCrewRead,
        dependencies=[Depends(require_crew_write)],
    )
    @limiter.limit("60/minute")
    async def update_crew(
        request: Request,
        crew_id: Annotated[UUID, Path()],
        body: VehicleCrewUpdate,
    ) -> VehicleCrewRead:
        """Update shift times / notes only."""
        service = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        patch = body.model_dump(exclude_unset=True)
        try:
            crew = await service.update_details(
                tenant_id,
                user_id,
                crew_id,
                shift_start=patch.get("shift_start"),
                shift_end=patch.get("shift_end"),
                notes=patch.get("notes"),
            )
        except VehicleCrewNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        return _to_crew_read(crew)

    @router.put(
        "/vehicle-crews/{crew_id}/members",
        response_model=VehicleCrewRead,
        dependencies=[Depends(require_crew_write)],
    )
    @limiter.limit("60/minute")
    async def replace_members(
        request: Request,
        crew_id: Annotated[UUID, Path()],
        body: VehicleCrewMembersReplace,
    ) -> VehicleCrewRead:
        """Atomically replace the crew roster."""
        service = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        members = [_schema_to_repo_member(m) for m in body.members]
        try:
            crew = await service.replace_members(tenant_id, user_id, crew_id, members)
        except VehicleCrewNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except (InvalidCrewMemberError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc
        return _to_crew_read(crew)

    @router.post(
        "/vehicle-crews/{crew_id}/members",
        response_model=CrewMemberRead,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(require_crew_write)],
    )
    @limiter.limit("60/minute")
    async def add_member(
        request: Request,
        crew_id: Annotated[UUID, Path()],
        body: SchemaCrewMemberInput,
    ) -> CrewMemberRead:
        """Add one member to the crew."""
        service = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        try:
            member = await service.add_member(
                tenant_id, user_id, crew_id, body.user_id, body.role_on_crew
            )
        except VehicleCrewNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except InvalidCrewMemberError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"detail": exc.message, "user_id": str(exc.user_id), "reason": exc.reason},
            ) from exc
        return CrewMemberRead(user_id=member.user_id, role_on_crew=member.role_on_crew)

    @router.delete(
        "/vehicle-crews/{crew_id}/members/{user_id_param}",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=[Depends(require_crew_write)],
    )
    @limiter.limit("60/minute")
    async def remove_member(
        request: Request,
        crew_id: Annotated[UUID, Path()],
        user_id_param: Annotated[UUID, Path(alias="user_id_param")],
    ) -> None:
        """Remove one member from the crew."""
        service = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        try:
            await service.remove_member(tenant_id, user_id, crew_id, user_id_param)
        except VehicleCrewNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    @router.delete(
        "/vehicle-crews/{crew_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=[Depends(require_crew_write)],
    )
    @limiter.limit("60/minute")
    async def delete_crew(
        request: Request,
        crew_id: Annotated[UUID, Path()],
    ) -> None:
        """Delete a crew and all its members."""
        service = service_provider()
        tenant_id = _tenant_id(request)
        user_id = _user_id(request)
        try:
            await service.delete(tenant_id, user_id, crew_id)
        except VehicleCrewNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return router


def _to_crew_read(crew) -> VehicleCrewRead:
    """Convert a VehicleCrew ORM object to VehicleCrewRead schema."""
    members = [
        CrewMemberRead(user_id=m.user_id, role_on_crew=m.role_on_crew) for m in (crew.members or [])
    ]
    return VehicleCrewRead(
        id=crew.id,
        tenant_id=crew.tenant_id,
        vehicle_id=crew.vehicle_id,
        work_date=crew.work_date,
        shift_start=crew.shift_start,
        shift_end=crew.shift_end,
        notes=crew.notes,
        created_by_user_id=crew.created_by_user_id,
        created_at=crew.created_at,
        updated_at=crew.updated_at,
        members=members,
    )
