"""Route and RouteStop models (Slice 14)."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from office_hero.models import Base


class Route(Base):
    """A daily route for one Vehicle, created atomically when dispatch is committed."""

    __tablename__ = "routes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    vehicle_id: Mapped[UUID] = mapped_column(ForeignKey("vehicles.id"), nullable=False)
    vehicle_crew_id: Mapped[UUID] = mapped_column(ForeignKey("vehicle_crews.id"), nullable=False)
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="committed")
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_distance_m: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_duration_s: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    option_kind_applied: Mapped[str | None] = mapped_column(String(20), nullable=True)
    committed_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    stops: Mapped[list[RouteStop]] = relationship(
        back_populates="route",
        cascade="all, delete-orphan",
        order_by="RouteStop.sequence_index",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "vehicle_id", "work_date", name="uq_route_tenant_vehicle_date"
        ),
        Index("idx_routes_tenant_work_date", "tenant_id", "work_date"),
        Index("idx_routes_tenant_status", "tenant_id", "status"),
        CheckConstraint(
            "status IN ('draft','committed','in_progress','complete','cancelled')",
            name="ck_route_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<Route(id={self.id}, vehicle_id={self.vehicle_id}, work_date={self.work_date}, status={self.status})>"


class RouteStop(Base):
    """One job stop within a Route, ordered by sequence_index."""

    __tablename__ = "route_stops"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    route_id: Mapped[UUID] = mapped_column(
        ForeignKey("routes.id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[UUID] = mapped_column(ForeignKey("jobs.id"), nullable=False)
    sequence_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    planned_eta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_arrived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    planned_distance_from_prev_m: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    planned_duration_from_prev_s: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    route: Mapped[Route] = relationship(back_populates="stops")

    __table_args__ = (
        UniqueConstraint("route_id", "sequence_index", name="uq_stop_route_sequence"),
        UniqueConstraint("route_id", "job_id", name="uq_stop_route_job"),
        Index("idx_route_stops_tenant_route", "tenant_id", "route_id"),
        CheckConstraint(
            "status IN ('pending','arrived','complete','skipped')",
            name="ck_stop_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<RouteStop(id={self.id}, route_id={self.route_id}, job_id={self.job_id}, seq={self.sequence_index})>"
