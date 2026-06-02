"""Vehicle location tracking table (Slice 15).

Revision ID: 0010_vehicle_location
Revises: 0009_routes
Create Date: 2026-06-02 03:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0010_vehicle_location"
down_revision = "0009_routes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create vehicle_locations table for time-series GPS tracking."""
    op.create_table(
        "vehicle_locations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("vehicle_id", sa.UUID(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("accuracy_meters", sa.Integer(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "vehicle_id", "recorded_at", name="uq_vehicle_location_recorded"),
    )

    # Index for querying latest location per vehicle
    op.create_index(
        "ix_vehicle_location_vehicle_date",
        "vehicle_locations",
        ["tenant_id", "vehicle_id", sa.desc("recorded_at")],
    )

    # Index for time-series queries
    op.create_index(
        "ix_vehicle_location_recorded_at",
        "vehicle_locations",
        ["tenant_id", "vehicle_id", "recorded_at"],
    )

    # Enable RLS on vehicle_locations
    op.execute("ALTER TABLE vehicle_locations ENABLE ROW LEVEL SECURITY;")

    # RLS policy: users can only see locations for vehicles in their tenant
    op.execute("""
        CREATE POLICY vehicle_locations_tenant_isolation
        ON vehicle_locations
        FOR ALL
        USING (tenant_id = current_setting('app.tenant_id')::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id')::uuid);
    """)


def downgrade() -> None:
    """Drop vehicle_locations table."""
    op.drop_table("vehicle_locations")
