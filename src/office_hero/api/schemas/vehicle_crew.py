"""Pydantic v2 request/response schemas for the VehicleCrew resource."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from office_hero.core.crew_role import CrewRole


class CrewMemberInput(BaseModel):
    """Single crew member specification within a crew create/replace payload."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    role_on_crew: CrewRole


class VehicleCrewCreate(BaseModel):
    """Request body for ``POST /vehicle-crews``."""

    model_config = ConfigDict(extra="forbid")

    vehicle_id: UUID
    work_date: date
    shift_start: time = Field(default=time(8, 0))
    shift_end: time = Field(default=time(17, 0))
    notes: str | None = None
    members: list[CrewMemberInput] = Field(min_length=1)

    @model_validator(mode="after")
    def _exactly_one_lead(self) -> Self:
        """Require exactly one LEAD in the member list."""
        leads = sum(1 for m in self.members if m.role_on_crew == CrewRole.LEAD)
        if leads == 0:
            raise ValueError("A crew must have exactly one member with role_on_crew='lead'")
        if leads > 1:
            raise ValueError("A crew cannot have more than one member with role_on_crew='lead'")
        return self


class VehicleCrewUpdate(BaseModel):
    """Request body for ``PATCH /vehicle-crews/{id}`` (shift/notes only)."""

    model_config = ConfigDict(extra="forbid")

    shift_start: time | None = None
    shift_end: time | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _at_least_one(self) -> Self:
        if not self.model_dump(exclude_unset=True):
            raise ValueError("PATCH must update at least one field")
        return self


class VehicleCrewMembersReplace(BaseModel):
    """Request body for ``PUT /vehicle-crews/{id}/members``."""

    model_config = ConfigDict(extra="forbid")

    members: list[CrewMemberInput] = Field(min_length=1)

    @model_validator(mode="after")
    def _exactly_one_lead(self) -> Self:
        leads = sum(1 for m in self.members if m.role_on_crew == CrewRole.LEAD)
        if leads == 0:
            raise ValueError("A crew must have exactly one member with role_on_crew='lead'")
        if leads > 1:
            raise ValueError("A crew cannot have more than one member with role_on_crew='lead'")
        return self


class CrewMemberRead(BaseModel):
    """Member row within a crew read response."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    user_id: UUID
    role_on_crew: str


class VehicleCrewRead(BaseModel):
    """Full crew read view with embedded member list."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    tenant_id: UUID
    vehicle_id: UUID
    work_date: date
    shift_start: time
    shift_end: time
    notes: str | None = None
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime
    members: list[CrewMemberRead] = Field(default_factory=list)


class VehicleCrewList(BaseModel):
    """Paginated list response for vehicle crews."""

    model_config = ConfigDict(extra="forbid")

    items: list[VehicleCrewRead]
    total: int


class CrewConflictRead(BaseModel):
    """Double-booked user on a given work date."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    crew_ids: list[UUID]
    work_date: date
