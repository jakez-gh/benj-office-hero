"""Composite indexes for the dispatch crew-lookup and contract generation queries

Revision ID: 0014_performance_indexes
Revises: 0013_archived_indexes
Create Date: 2026-06-13 00:00:00.000000

* ``vehicle_crews`` — ``get_for_vehicle_date`` filters on
  ``(tenant_id, vehicle_id, work_date)`` and runs on every dispatch commit,
  reassignment, and emergency dispatch. The existing
  ``idx_vehicle_crew_tenant_date(tenant_id, work_date)`` doesn't cover the
  ``vehicle_id`` predicate; add the three-column composite.
* ``contracts`` — ``list_due`` filters on ``(tenant_id, status='active',
  next_due <= as_of)`` and orders by ``next_due``. The separate
  ``(tenant_id, status)`` and ``(tenant_id, next_due)`` indexes each serve only
  part of it; a ``(tenant_id, status, next_due)`` composite serves the whole
  generation-pass query in one scan.
"""

from alembic import op

revision = "0014_performance_indexes"
down_revision = "0013_archived_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_vehicle_crew_tenant_vehicle_date",
        "vehicle_crews",
        ["tenant_id", "vehicle_id", "work_date"],
    )
    op.create_index(
        "idx_contracts_tenant_status_next_due",
        "contracts",
        ["tenant_id", "status", "next_due"],
    )


def downgrade() -> None:
    op.drop_index("idx_contracts_tenant_status_next_due", table_name="contracts")
    op.drop_index("idx_vehicle_crew_tenant_vehicle_date", table_name="vehicle_crews")
