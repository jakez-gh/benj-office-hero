"""Composite (tenant_id, archived) indexes on customers and vehicles

Revision ID: 0013_archived_indexes
Revises: 0012_backoffice_seam
Create Date: 2026-06-12 00:00:00.000000

CustomerRepository.list / list_summaries and VehicleRepository.list filter on
``(tenant_id, archived)`` for the dashboard list views, but neither table had a
supporting index — those filters fell back to a scan. These composite indexes
serve the hot "active rows for a tenant" path (and the rarer archived=true
admin view) directly.
"""

from alembic import op

revision = "0013_archived_indexes"
down_revision = "0012_backoffice_seam"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_customer_tenant_archived",
        "customers",
        ["tenant_id", "archived"],
    )
    op.create_index(
        "idx_vehicle_tenant_archived",
        "vehicles",
        ["tenant_id", "archived"],
    )


def downgrade() -> None:
    op.drop_index("idx_vehicle_tenant_archived", table_name="vehicles")
    op.drop_index("idx_customer_tenant_archived", table_name="customers")
