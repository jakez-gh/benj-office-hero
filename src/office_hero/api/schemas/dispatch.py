"""Pydantic schemas for the job dispatch endpoint (Slice 14)."""

from __future__ import annotations

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict


class JobDispatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vehicle_id: UUID
    scheduled_for: AwareDatetime


class JobDispatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    status: str
    assigned_vehicle_id: UUID
    scheduled_for: AwareDatetime
    title: str
    customer_id: UUID
    location_id: UUID
