"""Add assigned_vehicle_id to jobs table (Slice 13: routing engine)

Revision ID: 0007_job_vehicle_assignment
Revises: 0006_vehicles_and_crews
Create Date: 2026-05-28 00:00:00.000000

Adds:
  * ``assigned_vehicle_id`` UUID NULLABLE FK → vehicles.id on ``jobs``
  * Composite index ``idx_jobs_tenant_vehicle`` on ``(tenant_id, assigned_vehicle_id)``

No new RLS policy is needed — the jobs table RLS policy already pins
row visibility to ``current_setting('app.tenant_id')::uuid``.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0007_job_vehicle_assignment"
down_revision = "0006_vehicles_and_crews"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column(
            "assigned_vehicle_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_jobs_assigned_vehicle",
        "jobs",
        "vehicles",
        ["assigned_vehicle_id"],
        ["id"],
    )
    op.create_index(
        "idx_jobs_tenant_vehicle",
        "jobs",
        ["tenant_id", "assigned_vehicle_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_jobs_tenant_vehicle", table_name="jobs")
    op.drop_constraint("fk_jobs_assigned_vehicle", "jobs", type_="foreignkey")
    op.drop_column("jobs", "assigned_vehicle_id")
