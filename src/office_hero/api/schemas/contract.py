"""Pydantic v2 request/response schemas for the Contract resource (Slice 11)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from office_hero.api.schemas.job import JobSummary
from office_hero.core.contract_frequency import ContractFrequency


class ContractCreate(BaseModel):
    """Request body for ``POST /contracts``."""

    model_config = ConfigDict(extra="forbid")

    customer_id: UUID
    location_id: UUID
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    service_type: str | None = Field(default=None, max_length=120)
    priority: int = Field(default=50, ge=0, le=100)
    estimated_duration_min: int = Field(default=60, ge=5, le=1440)
    frequency: ContractFrequency
    start_date: date
    end_date: date | None = None

    custom_fields: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _end_after_start(self) -> Self:
        """Reject agreements that end before they begin."""
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class ContractUpdate(BaseModel):
    """Request body for ``PATCH /contracts/{id}`` (all fields optional).

    ``next_due`` is patchable on purpose — skipping or pulling forward the next
    visit is a routine dispatcher workflow.  ``frequency`` and ``status`` are
    immutable here (status uses the dedicated transition endpoints).
    """

    model_config = ConfigDict(extra="forbid")

    location_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    service_type: str | None = Field(default=None, max_length=120)
    priority: int | None = Field(default=None, ge=0, le=100)
    estimated_duration_min: int | None = Field(default=None, ge=5, le=1440)
    next_due: date | None = None
    end_date: date | None = None
    custom_fields: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _at_least_one(self) -> Self:
        """Reject empty patches — there has to be something to update."""
        if not self.model_dump(exclude_unset=True):
            raise ValueError("PATCH must update at least one field")
        return self


class ContractEndRequest(BaseModel):
    """Request body for ``POST /contracts/{id}/end``."""

    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=512)


class GenerateJobsRequest(BaseModel):
    """Request body for ``POST /contracts/generate-jobs``."""

    model_config = ConfigDict(extra="forbid")

    as_of: date | None = None


class ContractSummary(BaseModel):
    """Cheap projection used in list views."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    title: str
    status: str
    frequency: str
    next_due: date
    end_date: date | None = None
    customer_id: UUID
    location_id: UUID
    industry: str
    service_type: str | None = None
    priority: int


class ContractRead(BaseModel):
    """Full read view."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    tenant_id: UUID
    customer_id: UUID
    location_id: UUID
    industry: str
    title: str
    description: str | None = None
    service_type: str | None = None
    priority: int
    estimated_duration_min: int
    frequency: str
    start_date: date
    next_due: date
    end_date: date | None = None
    status: str
    paused_at: datetime | None = None
    ended_at: datetime | None = None
    end_reason: str | None = None
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    external_id: str | None = None
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class ContractList(BaseModel):
    """Paginated list response."""

    model_config = ConfigDict(extra="forbid")

    items: list[ContractSummary]
    total: int
    limit: int
    offset: int


class GenerateJobsResponse(BaseModel):
    """Response for ``POST /contracts/generate-jobs``."""

    model_config = ConfigDict(extra="forbid")

    generated: list[JobSummary]
    count: int
