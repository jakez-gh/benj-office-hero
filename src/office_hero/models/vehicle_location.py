"""Vehicle location tracking model (Slice 15)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from office_hero.db.base import Base


class VehicleLocation(Base):
    """Time-series record of a vehicle's GPS position."""

    __tablename__ = "vehicle_locations"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    vehicle_id: Mapped[UUID] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))

    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    accuracy_meters: Mapped[int] = mapped_column(Integer, nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "vehicle_id", "recorded_at", name="uq_vehicle_location_recorded"),
    )

    def __repr__(self) -> str:
        return f"<VehicleLocation(vehicle_id={self.vehicle_id}, lat={self.latitude}, lng={self.longitude}, recorded_at={self.recorded_at})>"
