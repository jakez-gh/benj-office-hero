"""contracts table with RLS; contract_id provenance column on jobs (Slice 11)

Revision ID: 0011_contracts
Revises: 0010_vehicle_locations_rls
Create Date: 2026-06-12 00:00:00.000000

* ``contracts`` table — recurring service agreements that generate Jobs
  * CHECK constraints on status / frequency / priority / duration
  * Indexes: ``(tenant_id, status)``, ``(tenant_id, next_due)``,
    ``(tenant_id, customer_id)``
  * RLS policy pinning row visibility to ``current_setting('app.tenant_id')``
    (ADR 053)
* ``jobs.contract_id`` — nullable FK recording which Contract generated a Job
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0011_contracts"
down_revision = "0010_vehicle_locations_rls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contracts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("industry", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("service_type", sa.String(120), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("estimated_duration_min", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("frequency", sa.String(20), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("next_due", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_reason", sa.Text(), nullable=True),
        sa.Column(
            "custom_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("created_by_user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_contracts_tenant"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], name="fk_contracts_customer"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], name="fk_contracts_location"),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], name="fk_contracts_created_by_user"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('active','paused','ended')",
            name="ck_contract_status",
        ),
        sa.CheckConstraint(
            "frequency IN ('weekly','biweekly','monthly','quarterly','semiannual','annual')",
            name="ck_contract_frequency",
        ),
        sa.CheckConstraint("priority BETWEEN 0 AND 100", name="ck_contract_priority"),
        sa.CheckConstraint(
            "estimated_duration_min BETWEEN 5 AND 1440",
            name="ck_contract_duration",
        ),
    )
    op.create_index("idx_contracts_tenant_status", "contracts", ["tenant_id", "status"])
    op.create_index("idx_contracts_tenant_next_due", "contracts", ["tenant_id", "next_due"])
    op.create_index("idx_contracts_tenant_customer", "contracts", ["tenant_id", "customer_id"])

    op.execute(
        """
        ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;
        CREATE POLICY contract_tenant_isolation ON contracts
            USING (tenant_id = current_setting('app.tenant_id')::uuid);
        """
    )

    op.add_column("jobs", sa.Column("contract_id", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_jobs_contract", "jobs", "contracts", ["contract_id"], ["id"])
    op.create_index("idx_jobs_tenant_contract", "jobs", ["tenant_id", "contract_id"])


def downgrade() -> None:
    op.drop_index("idx_jobs_tenant_contract", table_name="jobs")
    op.drop_constraint("fk_jobs_contract", "jobs", type_="foreignkey")
    op.drop_column("jobs", "contract_id")

    op.execute("DROP POLICY IF EXISTS contract_tenant_isolation ON contracts;")
    op.execute("ALTER TABLE contracts DISABLE ROW LEVEL SECURITY;")
    op.drop_index("idx_contracts_tenant_customer", table_name="contracts")
    op.drop_index("idx_contracts_tenant_next_due", table_name="contracts")
    op.drop_index("idx_contracts_tenant_status", table_name="contracts")
    op.drop_table("contracts")
