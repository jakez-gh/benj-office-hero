"""jobs table with RLS, industry column on tenants

Revision ID: 0005_jobs
Revises: 0004_customers_and_locations
Create Date: 2026-05-27 00:00:00.000000

Adds the Job aggregate for Slice 10 (Job Management). Includes:

  * ``ALTER TABLE tenants ADD COLUMN industry`` — default 'generic', back-fills existing rows
  * ``jobs`` table with all lifecycle timestamps and JSONB custom_fields
  * CHECK constraints on status, priority, and estimated_duration_min
  * Indexes: ``(tenant_id, status)``, ``(tenant_id, scheduled_for)``,
    ``(tenant_id, customer_id)``
  * GIN index on ``custom_fields`` with ``jsonb_path_ops`` (containment queries)
  * RLS policy pinning row visibility to ``current_setting('app.tenant_id')``
    (ADR 053)
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "0005_jobs"
down_revision = "0004_customers_and_locations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- tenants: add industry column (back-fills existing rows with 'generic') ---
    op.add_column(
        "tenants",
        sa.Column(
            "industry",
            sa.String(length=50),
            nullable=False,
            server_default="generic",
        ),
    )

    # --- jobs ---
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("industry", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("service_type", sa.String(length=120), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "estimated_duration_min",
            sa.Integer(),
            nullable=False,
            server_default="60",
        ),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column(
            "custom_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.CheckConstraint(
            "status IN ('pending','scheduled','in_progress','complete','cancelled')",
            name="ck_jobs_status",
        ),
        sa.CheckConstraint(
            "priority BETWEEN 0 AND 100",
            name="ck_jobs_priority",
        ),
        sa.CheckConstraint(
            "estimated_duration_min BETWEEN 5 AND 1440",
            name="ck_jobs_estimated_duration_min",
        ),
    )

    # Composite indexes for the most common query patterns.
    op.create_index(
        "idx_jobs_tenant_status",
        "jobs",
        ["tenant_id", "status"],
    )
    op.create_index(
        "idx_jobs_tenant_scheduled_for",
        "jobs",
        ["tenant_id", "scheduled_for"],
    )
    op.create_index(
        "idx_jobs_tenant_customer",
        "jobs",
        ["tenant_id", "customer_id"],
    )

    # GIN index for JSONB containment queries (@>).
    # jsonb_path_ops is chosen for smaller index size; note it only supports
    # @> — a ? key-existence index is a future addition if needed.
    op.execute("""
        CREATE INDEX idx_jobs_custom_fields_gin
            ON jobs USING gin (custom_fields jsonb_path_ops);
        """)

    # Row-level security — only rows whose tenant_id matches the session setting
    # are visible (ADR 053).
    op.execute("""
        ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
        CREATE POLICY job_tenant_isolation ON jobs
            USING (tenant_id = current_setting('app.tenant_id')::uuid);
        """)


def downgrade() -> None:
    # --- jobs ---
    op.execute("DROP POLICY IF EXISTS job_tenant_isolation ON jobs;")
    op.execute("ALTER TABLE jobs DISABLE ROW LEVEL SECURITY;")
    op.execute("DROP INDEX IF EXISTS idx_jobs_custom_fields_gin;")
    op.drop_index("idx_jobs_tenant_customer", table_name="jobs")
    op.drop_index("idx_jobs_tenant_scheduled_for", table_name="jobs")
    op.drop_index("idx_jobs_tenant_status", table_name="jobs")
    op.drop_table("jobs")

    # --- tenants ---
    op.drop_column("tenants", "industry")
