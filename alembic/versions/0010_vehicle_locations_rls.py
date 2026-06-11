"""Enable RLS on vehicle_locations (tenant isolation, ADR 053)

Revision ID: 0010_vehicle_locations_rls
Revises: 0009_routes
Create Date: 2026-06-11 00:00:00.000000

Migration 0008 created ``vehicle_locations`` without row-level security,
unlike every other tenant-scoped table. This adds the standard tenant
isolation policy keyed on ``current_setting('app.tenant_id')``.
"""

from alembic import op

revision = "0010_vehicle_locations_rls"
down_revision = "0009_routes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE vehicle_locations ENABLE ROW LEVEL SECURITY;
        CREATE POLICY vehicle_location_tenant_isolation ON vehicle_locations
            USING (tenant_id = current_setting('app.tenant_id')::uuid);
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS vehicle_location_tenant_isolation ON vehicle_locations;")
    op.execute("ALTER TABLE vehicle_locations DISABLE ROW LEVEL SECURITY;")
