"""customers and locations tables with RLS and trigram search

Revision ID: 0004_customers_and_locations
Revises: 0003_rate_limits_audit_events
Create Date: 2026-05-27 00:00:00.000000

Adds the Customer and Location aggregates for Slice 9 (Customer & Location
management). Includes:

  * ``customers`` and ``locations`` tables with FKs to ``tenants(id)``
  * unique partial index on ``(tenant_id, lower(email))`` (email scoped per
    tenant, active rows only)
  * GIN trigram index on ``customers.name`` for substring search
  * indexes on ``(tenant_id, customer_id)`` and ``(tenant_id, geocode_status)``
    so the geocoding worker can find pending rows quickly
  * RLS policies pinning row visibility to ``current_setting('app.tenant_id')``
    (ADR 053)

Extensions ``citext`` (case-insensitive email) and ``pg_trgm`` (trigram search)
are created with ``IF NOT EXISTS`` so reruns/replays are safe.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "0004_customers_and_locations"
down_revision = "0003_rate_limits_audit_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL extensions used by the indexes below.
    op.execute("CREATE EXTENSION IF NOT EXISTS citext;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # --- customers ---
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        # ``email`` is plain VARCHAR here; PostgreSQL CITEXT would simplify
        # case-insensitivity but increases swap cost (ADR 059). Instead we
        # enforce case-insensitive uniqueness via a partial functional index
        # on ``lower(email)`` below.
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("external_id", sa.String(length=255), nullable=True),
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
    )

    # Unique active email per tenant (case-insensitive). NULL emails are
    # allowed (partial index excludes them).
    op.execute(
        """
        CREATE UNIQUE INDEX uq_customer_tenant_email_active
            ON customers (tenant_id, lower(email))
            WHERE email IS NOT NULL AND archived = false;
        """
    )

    # Trigram GIN for fast ILIKE-style search on customer name.
    op.execute(
        """
        CREATE INDEX idx_customer_name_trgm
            ON customers USING GIN (name gin_trgm_ops);
        """
    )

    op.execute(
        """
        ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
        CREATE POLICY customer_tenant_isolation ON customers
            USING (tenant_id = current_setting('app.tenant_id')::uuid);
        """
    )

    # --- locations ---
    op.create_table(
        "locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("street", sa.String(length=255), nullable=False),
        sa.Column("street2", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.Column("state", sa.String(length=60), nullable=False),
        sa.Column("postal_code", sa.String(length=20), nullable=False),
        sa.Column(
            "country",
            sa.String(length=2),
            nullable=False,
            server_default="US",
        ),
        sa.Column("lat", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("lng", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("geocode_source", sa.String(length=50), nullable=True),
        sa.Column(
            "geocode_status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("geocoded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
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
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
    )

    op.create_index(
        "idx_location_tenant_customer",
        "locations",
        ["tenant_id", "customer_id"],
    )
    op.create_index(
        "idx_location_tenant_status",
        "locations",
        ["tenant_id", "geocode_status"],
    )

    op.execute(
        """
        ALTER TABLE locations ENABLE ROW LEVEL SECURITY;
        CREATE POLICY location_tenant_isolation ON locations
            USING (tenant_id = current_setting('app.tenant_id')::uuid);
        """
    )


def downgrade() -> None:
    # --- locations ---
    op.execute("DROP POLICY IF EXISTS location_tenant_isolation ON locations;")
    op.execute("ALTER TABLE locations DISABLE ROW LEVEL SECURITY;")
    op.drop_index("idx_location_tenant_status", table_name="locations")
    op.drop_index("idx_location_tenant_customer", table_name="locations")
    op.drop_table("locations")

    # --- customers ---
    op.execute("DROP POLICY IF EXISTS customer_tenant_isolation ON customers;")
    op.execute("ALTER TABLE customers DISABLE ROW LEVEL SECURITY;")
    op.execute("DROP INDEX IF EXISTS idx_customer_name_trgm;")
    op.execute("DROP INDEX IF EXISTS uq_customer_tenant_email_active;")
    op.drop_table("customers")

    # We deliberately do NOT drop the citext/pg_trgm extensions on downgrade —
    # other migrations / tables may use them and dropping a PostgreSQL
    # extension cascades into any objects that reference it.
