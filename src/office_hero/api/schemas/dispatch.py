"""Pydantic schemas for the job dispatch endpoint (Slice 14)."""

from __future__ import annotations

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class JobDispatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vehicle_id: UUID
    scheduled_for: AwareDatetime
    # Plan metrics from the chosen suggestion — recorded on the RouteStop so
    # the Routes view can show planned travel. Optional; default 0.
    travel_seconds: int = Field(default=0, ge=0, le=86_400)
    distance_meters: int = Field(default=0, ge=0, le=1_000_000)


class JobDispatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    status: str
    assigned_vehicle_id: UUID
    scheduled_for: AwareDatetime
    title: str
    customer_id: UUID
    location_id: UUID
    # Route the job was appended to (None only in unit-test wiring).
    route_id: UUID | None = None
