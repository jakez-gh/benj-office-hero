"""Pydantic v2 request/response schemas for the Job resource (Slice 10)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class JobCreate(BaseModel):
    """Request body for ``POST /jobs``."""

    model_config = ConfigDict(extra="forbid")

    customer_id: UUID
    location_id: UUID
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    priority: int = Field(default=50, ge=0, le=100)
    service_type: str | None = Field(default=None, max_length=120)
    requested_at: datetime | None = None
    requested_until: datetime | None = None
    estimated_duration_min: int = Field(default=60, ge=5, le=1440)
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class JobUpdate(BaseModel):
    """Request body for ``PATCH /jobs/{id}`` (all fields optional)."""

    model_config = ConfigDict(extra="forbid")

    location_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    priority: int | None = Field(default=None, ge=0, le=100)
    service_type: str | None = Field(default=None, max_length=120)
    requested_at: datetime | None = None
    requested_until: datetime | None = None
    estimated_duration_min: int | None = Field(default=None, ge=5, le=1440)
    custom_fields: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _at_least_one(self) -> Self:
        """Reject empty patches — there has to be something to update."""
        if not self.model_dump(exclude_unset=True):
            raise ValueError("PATCH must update at least one field")
        return self


class JobScheduleRequest(BaseModel):
    """Request body for ``POST /jobs/{id}/schedule``."""

    model_config = ConfigDict(extra="forbid")

    scheduled_for: datetime


class JobCompleteRequest(BaseModel):
    """Request body for ``POST /jobs/{id}/complete``."""

    model_config = ConfigDict(extra="forbid")

    completion_notes: str | None = Field(default=None, max_length=1024)


class JobCancelRequest(BaseModel):
    """Request body for ``POST /jobs/{id}/cancel``."""

    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=3, max_length=512)


class JobSummary(BaseModel):
    """Cheap projection used in list views."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    title: str
    status: str
    priority: int
    scheduled_for: datetime | None = None
    customer_id: UUID
    location_id: UUID
    industry: str
    service_type: str | None = None


class JobRead(BaseModel):
    """Full read view."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    tenant_id: UUID
    customer_id: UUID
    location_id: UUID
    industry: str
    title: str
    description: str | None = None
    status: str
    priority: int
    service_type: str | None = None
    requested_at: datetime | None = None
    requested_until: datetime | None = None
    estimated_duration_min: int
    scheduled_for: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancel_reason: str | None = None
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    external_id: str | None = None
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class JobList(BaseModel):
    """Paginated list response."""

    model_config = ConfigDict(extra="forbid")

    items: list[JobSummary]
    total: int
    limit: int
    offset: int
