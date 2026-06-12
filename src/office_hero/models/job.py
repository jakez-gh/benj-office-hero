"""Job ORM model — the operational unit of Office Hero.

A Job belongs to a :class:`~office_hero.models.customer.Customer` and a
:class:`~office_hero.models.location.Location`.  ``industry`` is copied from
the Tenant at creation time so historical jobs are unaffected by later Tenant
industry changes.  ``status`` follows the lifecycle defined in
:mod:`office_hero.core.job_status`; all transitions must go through
:class:`~office_hero.services.job_service.JobService._transition`.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from office_hero.models import Base

if TYPE_CHECKING:
    from office_hero.models.customer import Customer
    from office_hero.models.location import Location
    from office_hero.models.vehicle import Vehicle


class Job(Base):
    """Tenant-scoped operational job aggregate."""

    __tablename__ = "jobs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    customer_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    location_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("locations.id"), nullable=False
    )

    # Copied from Tenant.industry at create time (immutable per ADR).
    industry: Mapped[str] = mapped_column(String(50), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status is a plain varchar; the ORM does not enforce the domain rules —
    # that's exclusively the responsibility of JobService._transition().
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    # 0 = highest priority, 100 = lowest (routing-compatible scale).
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=50)

    service_type: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Customer's preferred time window (informational; Dispatcher may override).
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requested_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Used by the Slice-13 routing algorithm to estimate route duration.
    estimated_duration_min: Mapped[int] = mapped_column(Integer, nullable=False, default=60)

    # Lifecycle timestamps — set exactly once by JobService transition methods.
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Industry-specific metadata validated by the CustomFieldTemplate registry.
    custom_fields: Mapped[dict] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=False, server_default="{}"
    )

    # Back-office integration identifier (ADR 056).
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Slice 11: provenance link for jobs generated from a recurring Contract.
    contract_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=True
    )

    # Slice 13: vehicle assigned by the routing / scheduling engine.
    assigned_vehicle_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=True
    )

    created_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    customer: Mapped[Customer] = relationship("Customer")
    location: Mapped[Location] = relationship("Location")
    vehicle: Mapped[Vehicle | None] = relationship("Vehicle")

    __table_args__ = (
        # Dispatch dashboard: filter by status within a tenant.
        Index("idx_jobs_tenant_status", "tenant_id", "status"),
        # Daily-view + routing: jobs scheduled for a given date.
        Index("idx_jobs_tenant_scheduled_for", "tenant_id", "scheduled_for"),
        # Customer detail view: all jobs for a customer.
        Index("idx_jobs_tenant_customer", "tenant_id", "customer_id"),
        # Routing engine: jobs assigned to a specific vehicle within a tenant.
        Index("idx_jobs_tenant_vehicle", "tenant_id", "assigned_vehicle_id"),
        # GIN index for JSONB containment queries on custom_fields.
        # jsonb_path_ops is chosen for smallest index size; note it only
        # supports @> (containment) — a ? key-existence index is future work.
        Index(
            "idx_jobs_custom_fields_gin",
            "custom_fields",
            postgresql_using="gin",
            postgresql_ops={"custom_fields": "jsonb_path_ops"},
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Job(id={self.id}, title={self.title!r}, "
            f"status={self.status}, tenant_id={self.tenant_id})>"
        )
