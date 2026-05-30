"""Request/response schemas for vehicle location endpoints (Slice 15)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class VehicleLocationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat: Decimal = Field(..., ge=-90, le=90)
    lng: Decimal = Field(..., ge=-180, le=180)
    accuracy_m: Decimal | None = Field(default=None, ge=0)
    recorded_at: AwareDatetime


class VehicleLocationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    vehicle_id: UUID
    lat: Decimal
    lng: Decimal
    accuracy_m: Decimal | None
    recorded_at: datetime
