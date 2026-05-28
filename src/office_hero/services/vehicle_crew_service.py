"""VehicleCrewService — orchestrates VehicleCrew lifecycle with validation.

Key invariants enforced at the service layer:
* Exactly one member with role_on_crew == LEAD per crew.
* All members must be active users in the same tenant with role Technician or
  TechnicianHelper — otherwise :class:`InvalidCrewMemberError` is raised.
* work_date must not be more than 30 days in the past.
* shift_end must be after shift_start.
* The LEAD cannot be removed without being replaced.

The unique (vehicle, date) invariant is enforced by the repository layer
(which converts IntegrityError → CrewAssignmentConflictError).
"""

from __future__ import annotations

from datetime import date, time
from typing import Any, Protocol
from uuid import UUID

from office_hero.core.crew_role import CrewRole
from office_hero.core.exceptions import (
    InvalidCrewMemberError,
    VehicleCrewNotFoundError,
    VehicleNotFoundError,
)
from office_hero.core.logging import get_logger
from office_hero.core.roles import Role
from office_hero.models.vehicle_crew import VehicleCrew
from office_hero.repositories.vehicle_crew_repository import (
    CrewMemberInput,
    VehicleCrewRepositoryProtocol,
)
from office_hero.repositories.vehicle_repository import VehicleRepositoryProtocol

log = get_logger(__name__)

# How far back in the past is a work_date allowed to be?
_MAX_BACKDATED_DAYS = 30

# RBAC roles permitted on a crew
_CREW_ELIGIBLE_ROLES = {Role.Technician.value, Role.TechnicianHelper.value}


class AuditPublisher(Protocol):
    """Minimal audit-publisher contract (ADR 063)."""

    async def log_event(
        self,
        event_type: str,
        details: dict,
        tenant_id: UUID,
        user_id: UUID | None = None,
        request_id: UUID | None = None,
    ) -> None: ...


class UserRepositoryProtocol(Protocol):
    """Minimal user lookup shape used by the crew service."""

    async def get_by_id(self, user_id: UUID, tenant_id: UUID) -> Any | None: ...


def _crew_summary(crew: VehicleCrew) -> dict[str, Any]:
    return {
        "crew_id": str(crew.id),
        "vehicle_id": str(crew.vehicle_id),
        "work_date": str(crew.work_date),
        "member_user_ids": [str(m.user_id) for m in (crew.members or [])],
    }


def _lead_count(members: list[CrewMemberInput]) -> int:
    return sum(1 for m in members if m.role_on_crew == CrewRole.LEAD)


class VehicleCrewService:
    """Business orchestration for :class:`VehicleCrew` management."""

    def __init__(
        self,
        crew_repo: VehicleCrewRepositoryProtocol,
        vehicle_repo: VehicleRepositoryProtocol,
        user_repo: UserRepositoryProtocol,
        audit: AuditPublisher,
    ):
        """Inject repos and audit publisher (DI)."""
        self.crew_repo = crew_repo
        self.vehicle_repo = vehicle_repo
        self.user_repo = user_repo
        self.audit = audit

    async def _validate_members(
        self,
        tenant_id: UUID,
        members: list[CrewMemberInput],
    ) -> None:
        """Validate each member is an active Technician/TechnicianHelper in the tenant."""
        for m in members:
            user = await self.user_repo.get_by_id(m.user_id, tenant_id)
            if user is None:
                raise InvalidCrewMemberError(
                    message=f"User {m.user_id} not found in tenant",
                    user_id=m.user_id,
                    reason="not_in_tenant",
                )
            if not user.active:
                raise InvalidCrewMemberError(
                    message=f"User {m.user_id} is inactive",
                    user_id=m.user_id,
                    reason="inactive",
                )
            if user.role not in _CREW_ELIGIBLE_ROLES:
                raise InvalidCrewMemberError(
                    message=(
                        f"User {m.user_id} has role {user.role!r}; only Technician"
                        " and TechnicianHelper can be crew members"
                    ),
                    user_id=m.user_id,
                    reason="ineligible_role",
                )

    async def _validate_lead_invariant(self, members: list[CrewMemberInput]) -> None:
        """Raise ValueError if not exactly one LEAD."""
        leads = _lead_count(members)
        if leads == 0:
            raise ValueError("A crew must have exactly one LEAD member")
        if leads > 1:
            raise ValueError("A crew cannot have more than one LEAD member")

    async def create(
        self,
        tenant_id: UUID,
        user_id: UUID,
        *,
        vehicle_id: UUID,
        work_date: date,
        shift_start: time,
        shift_end: time,
        notes: str | None,
        members: list[CrewMemberInput],
    ) -> VehicleCrew:
        """Create a crew after running all service-layer invariants.

        Raises:
            VehicleNotFoundError: vehicle doesn't exist or is archived.
            ValueError: work_date too far in the past, shift ordering bad,
                or lead count wrong.
            InvalidCrewMemberError: a member fails eligibility checks.
            CrewAssignmentConflictError: a crew already exists for this
                (vehicle, date) — propagated from the repo layer.
        """
        # Vehicle must exist and not be archived
        vehicle = await self.vehicle_repo.get_by_id(vehicle_id, tenant_id)
        if vehicle is None or vehicle.archived:
            raise VehicleNotFoundError(f"Vehicle {vehicle_id} not found or is archived")

        # work_date must not be too far in the past
        today = date.today()
        delta = (today - work_date).days
        if delta > _MAX_BACKDATED_DAYS:
            raise ValueError(f"work_date is {delta} days in the past (max {_MAX_BACKDATED_DAYS})")

        # shift ordering
        if shift_end <= shift_start:
            raise ValueError("shift_end must be after shift_start")

        # lead invariant
        await self._validate_lead_invariant(members)

        # member eligibility
        await self._validate_members(tenant_id, members)

        crew = await self.crew_repo.create(
            tenant_id,
            vehicle_id=vehicle_id,
            work_date=work_date,
            shift_start=shift_start,
            shift_end=shift_end,
            notes=notes,
            created_by_user_id=user_id,
            members=members,
        )
        await self.audit.log_event(
            event_type="crew.created",
            details=_crew_summary(crew),
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return crew

    async def get(self, tenant_id: UUID, crew_id: UUID) -> VehicleCrew:
        """Fetch a crew or raise :class:`VehicleCrewNotFoundError`."""
        crew = await self.crew_repo.get_by_id(crew_id, tenant_id)
        if crew is None:
            raise VehicleCrewNotFoundError(f"VehicleCrew {crew_id} not found")
        return crew

    async def list_for_date(self, tenant_id: UUID, work_date: date) -> list[VehicleCrew]:
        """Return all crews for the date."""
        return await self.crew_repo.list_for_date(tenant_id, work_date)

    async def get_for_vehicle_date(
        self, tenant_id: UUID, vehicle_id: UUID, work_date: date
    ) -> VehicleCrew | None:
        """Return the crew for a specific vehicle and date."""
        return await self.crew_repo.get_for_vehicle_date(tenant_id, vehicle_id, work_date)

    async def update_details(
        self,
        tenant_id: UUID,
        user_id: UUID,
        crew_id: UUID,
        *,
        shift_start: time | None = None,
        shift_end: time | None = None,
        notes: str | None = None,
    ) -> VehicleCrew:
        """Update shift/notes only; member changes go through dedicated endpoints."""
        await self.get(tenant_id, crew_id)
        updated = await self.crew_repo.update(
            crew_id, tenant_id, shift_start=shift_start, shift_end=shift_end, notes=notes
        )
        await self.audit.log_event(
            event_type="crew.updated",
            details={"crew_id": str(crew_id)},
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return updated

    async def replace_members(
        self,
        tenant_id: UUID,
        user_id: UUID,
        crew_id: UUID,
        members: list[CrewMemberInput],
    ) -> VehicleCrew:
        """Atomically replace the crew roster after re-validating invariants."""
        await self.get(tenant_id, crew_id)
        await self._validate_lead_invariant(members)
        await self._validate_members(tenant_id, members)
        updated = await self.crew_repo.replace_members(crew_id, tenant_id, members)
        await self.audit.log_event(
            event_type="crew.members_replaced",
            details={
                "crew_id": str(crew_id),
                "member_user_ids": [str(m.user_id) for m in members],
            },
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return updated

    async def add_member(
        self,
        tenant_id: UUID,
        user_id: UUID,
        crew_id: UUID,
        user_id_to_add: UUID,
        role_on_crew: CrewRole,
    ) -> Any:
        """Add one member after eligibility validation."""
        crew = await self.get(tenant_id, crew_id)
        new_input = CrewMemberInput(user_id=user_id_to_add, role_on_crew=role_on_crew)
        await self._validate_members(tenant_id, [new_input])
        member = await self.crew_repo.add_member(crew_id, tenant_id, user_id_to_add, role_on_crew)
        await self.audit.log_event(
            event_type="crew.member_added",
            details={"crew_id": str(crew_id), "user_id": str(user_id_to_add)},
            tenant_id=tenant_id,
            user_id=user_id,
        )
        return member

    async def remove_member(
        self,
        tenant_id: UUID,
        user_id: UUID,
        crew_id: UUID,
        user_id_to_remove: UUID,
    ) -> None:
        """Remove a member; refuses to remove the LEAD without a replacement."""
        crew = await self.get(tenant_id, crew_id)
        # Find the member's role
        member_row = next((m for m in (crew.members or []) if m.user_id == user_id_to_remove), None)
        if member_row is not None and member_row.role_on_crew == str(CrewRole.LEAD):
            # Count remaining members after this removal
            remaining = [m for m in (crew.members or []) if m.user_id != user_id_to_remove]
            remaining_leads = sum(1 for m in remaining if m.role_on_crew == str(CrewRole.LEAD))
            if remaining_leads == 0:
                raise ValueError("Cannot remove the LEAD without assigning a replacement first")

        await self.crew_repo.remove_member(crew_id, tenant_id, user_id_to_remove)
        await self.audit.log_event(
            event_type="crew.member_removed",
            details={"crew_id": str(crew_id), "user_id": str(user_id_to_remove)},
            tenant_id=tenant_id,
            user_id=user_id,
        )

    async def delete(self, tenant_id: UUID, user_id: UUID, crew_id: UUID) -> None:
        """Delete the crew (cascade deletes members).

        Once Slice 14 (routing) lands, this will also check for Route references.
        For now, deletion is always allowed after finding the crew.
        """
        crew = await self.get(tenant_id, crew_id)
        details = {
            "crew_id": str(crew_id),
            "work_date": str(crew.work_date),
            "vehicle_id": str(crew.vehicle_id),
        }
        await self.crew_repo.delete(crew_id, tenant_id)
        await self.audit.log_event(
            event_type="crew.deleted",
            details=details,
            tenant_id=tenant_id,
            user_id=user_id,
        )

    async def conflicts_for_date(
        self, tenant_id: UUID, work_date: date
    ) -> list[tuple[UUID, list[UUID]]]:
        """Return double-booked user IDs with their conflicting crew IDs."""
        return await self.crew_repo.find_user_crew_conflicts(tenant_id, work_date)
