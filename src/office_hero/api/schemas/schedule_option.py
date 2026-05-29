"""Pydantic schemas for the schedule-options endpoint (Slice 13)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScheduleOptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    window_start: datetime
    window_end: datetime
    max_results: int = Field(default=3, ge=1, le=10)


class ScheduleOptionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vehicle_id: UUID
    vehicle_display: str
    suggested_start: datetime
    travel_seconds: int
    distance_meters: int
    rank: int


class ScheduleOptionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: UUID
    options: list[ScheduleOptionItem]
