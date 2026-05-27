"""Pydantic v2 schemas for the Location resource (HLD A03)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LocationCreate(BaseModel):
    """Request body for ``POST /customers/{customer_id}/locations``."""

    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, max_length=255)
    street: str = Field(min_length=1, max_length=255)
    street2: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=1, max_length=120)
    state: str = Field(min_length=1, max_length=60)
    postal_code: str = Field(min_length=1, max_length=20)
    country: str = Field(default="US", min_length=2, max_length=2)
    geocode: bool = True


class LocationUpdate(BaseModel):
    """Request body for ``PATCH /locations/{id}``."""

    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, max_length=255)
    street: str | None = Field(default=None, max_length=255)
    street2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=60)
    postal_code: str | None = Field(default=None, max_length=20)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    regeocode: bool | Literal["auto"] = "auto"

    @model_validator(mode="after")
    def _at_least_one_field(self) -> Self:
        """Patch must touch something beyond ``regeocode``."""
        data = self.model_dump(exclude_unset=True)
        data.pop("regeocode", None)
        if not data:
            raise ValueError("PATCH must update at least one field")
        return self


class LocationCoordinatesSet(BaseModel):
    """Request body for the manual coordinates override endpoint."""

    model_config = ConfigDict(extra="forbid")

    lat: float = Field(ge=-90.0, le=90.0)
    lng: float = Field(ge=-180.0, le=180.0)


class LocationRead(BaseModel):
    """Full read view of a Location."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    tenant_id: UUID
    customer_id: UUID
    label: str | None = None
    street: str
    street2: str | None = None
    city: str
    state: str
    postal_code: str
    country: str
    lat: float | None = None
    lng: float | None = None
    geocode_source: str | None = None
    geocode_status: str
    geocoded_at: datetime | None = None
    archived: bool
    created_at: datetime
    updated_at: datetime
