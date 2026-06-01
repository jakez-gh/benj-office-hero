"""Pydantic schemas for route management (Slice 14)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, field_validator


class RouteStopRead(BaseModel):
    """A single RouteStop with embedded Job summary."""

    id: UUID
    route_id: UUID
    job_id: UUID
    sequence_index: int
    status: str
    planned_eta: AwareDatetime | None = None
    actual_arrived_at: AwareDatetime | None = None
    actual_completed_at: AwareDatetime | None = None
    planned_distance_from_prev_m: int = 0
    planned_duration_from_prev_s: int = 0


class VehicleSummary(BaseModel):
    """Summary of a Vehicle for route response."""

    id: UUID
    nickname: str
    license_plate: str


class VehicleCrewSummary(BaseModel):
    """Summary of a VehicleCrew for route response."""

    id: UUID
    vehicle_id: UUID
    work_date: date


class RouteRead(BaseModel):
    """A committed Route with all stops and metadata."""

    id: UUID
    tenant_id: UUID
    vehicle_id: UUID
    vehicle_crew_id: UUID
    work_date: date
    status: str
    committed_at: AwareDatetime | None = None
    started_at: AwareDatetime | None = None
    completed_at: AwareDatetime | None = None
    cancelled_at: AwareDatetime | None = None
    cancel_reason: str | None = None
    total_distance_m: int = 0
    total_duration_s: int = 0
    option_kind_applied: str | None = None
    committed_by_user_id: UUID | None = None
    notes: str | None = None
    stops: list[RouteStopRead] = []
    vehicle: VehicleSummary | None = None
    crew: VehicleCrewSummary | None = None


class RouteListResponse(BaseModel):
    """Paginated list of routes."""

    items: list[RouteRead]
    total: int


class DispatchCommitRequest(BaseModel):
    """Request to commit a dispatch (create/update a Route)."""

    model_config = ConfigDict(extra="forbid")

    date: date
    option_kind: Literal["nearest", "earliest", "balanced"] | None = None
    manual_vehicle_id: UUID | None = None
    manual_sequence: list[UUID] | None = None
    notes: str | None = None

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: str | None) -> str | None:
        if v and len(v) > 2048:
            raise ValueError("notes must be <= 2048 characters")
        return v

    def __init__(self, **data):
        super().__init__(**data)
        # Validate exactly one of option_kind or (manual_vehicle_id, manual_sequence)
        has_option = self.option_kind is not None
        has_manual = (
            self.manual_vehicle_id is not None and self.manual_sequence is not None
        )
        if not (has_option ^ has_manual):
            raise ValueError(
                "Exactly one of option_kind or (manual_vehicle_id, manual_sequence) must be provided"
            )


class RouteCancelRequest(BaseModel):
    """Request to cancel a route."""

    model_config = ConfigDict(extra="forbid")

    reason: str

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not (3 <= len(v) <= 512):
            raise ValueError("reason must be 3..512 characters")
        return v


class StopSkipRequest(BaseModel):
    """Request to skip a route stop."""

    model_config = ConfigDict(extra="forbid")

    reason: str

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not (3 <= len(v) <= 512):
            raise ValueError("reason must be 3..512 characters")
        return v
