"""Pydantic v2 request/response schemas for the Vehicle resource."""

from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class VehicleCreate(BaseModel):
    """Request body for ``POST /vehicles``."""

    model_config = ConfigDict(extra="forbid")

    license_plate: str = Field(min_length=1, max_length=20)
    nickname: str | None = Field(default=None, max_length=120)
    make: str | None = Field(default=None, max_length=60)
    model: str | None = Field(default=None, max_length=60)
    year: int | None = Field(default=None, ge=1980, le=2100)
    vin: str | None = Field(default=None, min_length=17, max_length=17)
    gps_device_id: str | None = Field(default=None, max_length=120)
    capacity_kg: int | None = Field(default=None, ge=0)
    home_base_lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    home_base_lng: float | None = Field(default=None, ge=-180.0, le=180.0)
    notes: str | None = None


class VehicleUpdate(BaseModel):
    """Request body for ``PATCH /vehicles/{id}`` (all optional)."""

    model_config = ConfigDict(extra="forbid")

    license_plate: str | None = Field(default=None, min_length=1, max_length=20)
    nickname: str | None = Field(default=None, max_length=120)
    make: str | None = Field(default=None, max_length=60)
    model: str | None = Field(default=None, max_length=60)
    year: int | None = Field(default=None, ge=1980, le=2100)
    vin: str | None = Field(default=None, min_length=17, max_length=17)
    gps_device_id: str | None = Field(default=None, max_length=120)
    capacity_kg: int | None = Field(default=None, ge=0)
    home_base_lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    home_base_lng: float | None = Field(default=None, ge=-180.0, le=180.0)
    notes: str | None = None

    @model_validator(mode="after")
    def _at_least_one(self) -> Self:
        """Reject empty patches."""
        if not self.model_dump(exclude_unset=True):
            raise ValueError("PATCH must update at least one field")
        return self


class VehicleSummary(BaseModel):
    """Cheap projection used in list views."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    license_plate: str
    nickname: str | None = None
    make: str | None = None
    model: str | None = None
    year: int | None = None
    archived: bool


class VehicleRead(BaseModel):
    """Full read view."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    tenant_id: UUID
    license_plate: str
    nickname: str | None = None
    make: str | None = None
    model: str | None = None
    year: int | None = None
    vin: str | None = None
    gps_device_id: str | None = None
    capacity_kg: int | None = None
    home_base_lat: float | None = None
    home_base_lng: float | None = None
    notes: str | None = None
    archived: bool
    created_at: datetime
    updated_at: datetime


class VehicleList(BaseModel):
    """Paginated list response."""

    model_config = ConfigDict(extra="forbid")

    items: list[VehicleSummary]
    total: int
    limit: int
    offset: int
