"""vehicles and vehicle_crews tables with RLS

Revision ID: 0005_vehicles_and_crews
Revises: 0004_customers_and_locations
Create Date: 2026-05-28 00:00:00.000000

Adds the Vehicle aggregate and date-scoped VehicleCrew / VehicleCrewMember
tables for Slice 12 (Vehicle & VehicleCrew management). Includes:

  * ``vehicles`` table with FKs to ``tenants(id)``
  * Partial unique index ``uq_vehicle_tenant_plate_active`` on
    ``(tenant_id, license_plate)`` WHERE ``archived = false``
  * Partial unique index ``uq_vehicle_tenant_vin`` on ``(tenant_id, vin)``
    WHERE ``vin IS NOT NULL``
  * CHECK constraints: ``year BETWEEN 1980 AND 2100``,
    ``capacity_kg >= 0``
  * RLS policy pinning row visibility to ``current_setting('app.tenant_id')``
    (ADR 053)
  * ``vehicle_crews`` table: unique ``(tenant_id, vehicle_id, work_date)``;
    index on ``(tenant_id, work_date)`` for the daily dispatch view
  * ``vehicle_crew_members`` table: unique ``(crew_id, user_id)``; CHECK on
    ``role_on_crew``; ``tenant_id`` denormalised for RLS without join
  * RLS policies on all three tables
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "0005_vehicles_and_crews"
down_revision = "0004_customers_and_locations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- vehicles ---
    op.create_table(
        "vehicles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("license_plate", sa.String(length=20), nullable=False),
        sa.Column("nickname", sa.String(length=120), nullable=True),
        sa.Column("make", sa.String(length=60), nullable=True),
        sa.Column("model", sa.String(length=60), nullable=True),
        sa.Column(
            "year",
            sa.Integer(),
            sa.CheckConstraint("year BETWEEN 1980 AND 2100", name="ck_vehicle_year"),
            nullable=True,
        ),
        sa.Column("vin", sa.String(length=17), nullable=True),
        sa.Column("gps_device_id", sa.String(length=120), nullable=True),
        sa.Column(
            "capacity_kg",
            sa.Integer(),
            sa.CheckConstraint("capacity_kg >= 0", name="ck_vehicle_capacity_kg"),
            nullable=True,
        ),
        sa.Column("home_base_lat", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("home_base_lng", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
    )

    # Unique active license plate per tenant. NULL plates are not allowed
    # (NOT NULL column), but archived vehicles release the plate.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_vehicle_tenant_plate_active
            ON vehicles (tenant_id, license_plate)
            WHERE archived = false;
        """
    )

    # Unique VIN per tenant where set (partial; allows multiple NULLs).
    op.execute(
        """
        CREATE UNIQUE INDEX uq_vehicle_tenant_vin
            ON vehicles (tenant_id, vin)
            WHERE vin IS NOT NULL;
        """
    )

    op.execute(
        """
        ALTER TABLE vehicles ENABLE ROW LEVEL SECURITY;
        CREATE POLICY vehicle_tenant_isolation ON vehicles
            USING (tenant_id = current_setting('app.tenant_id')::uuid);
        """
    )

    # --- vehicle_crews ---
    op.create_table(
        "vehicle_crews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column(
            "shift_start",
            sa.Time(),
            nullable=False,
            server_default="08:00:00",
        ),
        sa.Column(
            "shift_end",
            sa.Time(),
            nullable=False,
            server_default="17:00:00",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.UniqueConstraint(
            "tenant_id",
            "vehicle_id",
            "work_date",
            name="uq_vehicle_crew_vehicle_date",
        ),
    )

    # Index for the daily dispatch view: "all crews for date X in tenant Y"
    op.create_index(
        "idx_vehicle_crew_tenant_date",
        "vehicle_crews",
        ["tenant_id", "work_date"],
    )

    op.execute(
        """
        ALTER TABLE vehicle_crews ENABLE ROW LEVEL SECURITY;
        CREATE POLICY vehicle_crew_tenant_isolation ON vehicle_crews
            USING (tenant_id = current_setting('app.tenant_id')::uuid);
        """
    )

    # --- vehicle_crew_members ---
    op.create_table(
        "vehicle_crew_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("crew_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "role_on_crew",
            sa.String(length=20),
            sa.CheckConstraint(
                "role_on_crew IN ('lead', 'helper', 'trainee')",
                name="ck_crew_member_role",
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(
            ["crew_id"], ["vehicle_crews.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("crew_id", "user_id", name="uq_crew_member_user"),
    )

    op.execute(
        """
        ALTER TABLE vehicle_crew_members ENABLE ROW LEVEL SECURITY;
        CREATE POLICY vehicle_crew_member_tenant_isolation ON vehicle_crew_members
            USING (tenant_id = current_setting('app.tenant_id')::uuid);
        """
    )


def downgrade() -> None:
    # --- vehicle_crew_members ---
    op.execute(
        "DROP POLICY IF EXISTS vehicle_crew_member_tenant_isolation ON vehicle_crew_members;"
    )
    op.execute("ALTER TABLE vehicle_crew_members DISABLE ROW LEVEL SECURITY;")
    op.drop_table("vehicle_crew_members")

    # --- vehicle_crews ---
    op.execute(
        "DROP POLICY IF EXISTS vehicle_crew_tenant_isolation ON vehicle_crews;"
    )
    op.execute("ALTER TABLE vehicle_crews DISABLE ROW LEVEL SECURITY;")
    op.drop_index("idx_vehicle_crew_tenant_date", table_name="vehicle_crews")
    op.drop_table("vehicle_crews")

    # --- vehicles ---
    op.execute("DROP POLICY IF EXISTS vehicle_tenant_isolation ON vehicles;")
    op.execute("ALTER TABLE vehicles DISABLE ROW LEVEL SECURITY;")
    op.execute("DROP INDEX IF EXISTS uq_vehicle_tenant_vin;")
    op.execute("DROP INDEX IF EXISTS uq_vehicle_tenant_plate_active;")
    op.drop_table("vehicles")
