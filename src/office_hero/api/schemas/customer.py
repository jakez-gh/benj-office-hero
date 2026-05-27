"""Pydantic v2 request/response schemas for the Customer resource (HLD A03)."""

from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from office_hero.api.schemas.location import LocationRead


class CustomerCreate(BaseModel):
    """Request body for ``POST /customers``."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    notes: str | None = None


class CustomerUpdate(BaseModel):
    """Request body for ``PATCH /customers/{id}`` (all optional)."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    notes: str | None = None

    @model_validator(mode="after")
    def _at_least_one(self) -> Self:
        """Reject empty patches — there has to be something to update."""
        if not self.model_dump(exclude_unset=True):
            raise ValueError("PATCH must update at least one field")
        return self


class CustomerSummary(BaseModel):
    """Cheap projection used in list views."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    name: str
    archived: bool
    location_count: int = 0
    primary_city: str | None = None


class CustomerRead(BaseModel):
    """Full read view (optionally with embedded locations)."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    email: str | None = None
    phone: str | None = None
    notes: str | None = None
    archived: bool
    external_id: str | None = None
    created_at: datetime
    updated_at: datetime
    locations: list[LocationRead] = Field(default_factory=list)


class CustomerList(BaseModel):
    """Paginated list response."""

    model_config = ConfigDict(extra="forbid")

    items: list[CustomerSummary]
    total: int
    limit: int
    offset: int
