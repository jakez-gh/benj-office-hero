"""Vehicle ORM model — long-lived physical truck/van aggregate.

A Vehicle is tenant-scoped and participates in date-scoped VehicleCrew
assignments (see :mod:`office_hero.models.vehicle_crew`). Archived vehicles
are excluded from routing candidate lists (Slice 13+).

Tenant isolation is enforced by RLS (ADR 053); the application also re-checks
tenant ownership defensively on every read/write (defence in depth).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from office_hero.models import Base

if TYPE_CHECKING:
    from office_hero.models.vehicle_crew import VehicleCrew


class Vehicle(Base):
    """Tenant-scoped vehicle (physical truck/van) aggregate."""

    __tablename__ = "vehicles"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    license_plate: Mapped[str] = mapped_column(String(20), nullable=False)
    nickname: Mapped[str | None] = mapped_column(String(120), nullable=True)
    make: Mapped[str | None] = mapped_column(String(60), nullable=True)
    model: Mapped[str | None] = mapped_column(String(60), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vin: Mapped[str | None] = mapped_column(String(17), nullable=True)
    # Optional GPS hardware ID. Slice 15 (vehicle location tracking) will use
    # this to disambiguate when phone GPS is unavailable; NULL = phone-only
    # tracking mode.
    gps_device_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Informational payload limit. Not enforced as a routing constraint in v1
    # (see risk callout in design 013); may feed routing constraints later.
    capacity_kg: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_base_lat: Mapped[float | None] = mapped_column(
        Numeric(precision=9, scale=6), nullable=True
    )
    home_base_lng: Mapped[float | None] = mapped_column(
        Numeric(precision=9, scale=6), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    crews: Mapped[list[VehicleCrew]] = relationship(
        "VehicleCrew",
        back_populates="vehicle",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Vehicle(id={self.id}, license_plate={self.license_plate!r},"
            f" tenant_id={self.tenant_id})>"
        )
