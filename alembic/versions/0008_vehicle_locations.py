"""Create vehicle_locations table (Slice 15: vehicle location tracking)

Revision ID: 0008_vehicle_locations
Revises: 0007_job_vehicle_assignment
Create Date: 2026-05-30 00:00:00.000000

Adds:
  * ``vehicle_locations`` table — time-series GPS positions
  * Composite index on ``(tenant_id, vehicle_id, recorded_at)`` for
    efficient latest-position lookup per vehicle
"""

import sqlalchemy as sa

from alembic import op

revision = "0008_vehicle_locations"
down_revision = "0007_job_vehicle_assignment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vehicle_locations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("vehicle_id", sa.UUID(), nullable=False),
        sa.Column("lat", sa.Numeric(9, 6), nullable=False),
        sa.Column("lng", sa.Numeric(9, 6), nullable=False),
        sa.Column("accuracy_m", sa.Numeric(8, 2), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["vehicle_id"], ["vehicles.id"], name="fk_vehicle_locations_vehicle"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_vehicle_locations_tenant_vehicle_recorded",
        "vehicle_locations",
        ["tenant_id", "vehicle_id", "recorded_at"],
    )
    op.create_index(
        "idx_vehicle_locations_tenant_id",
        "vehicle_locations",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_vehicle_locations_tenant_id", table_name="vehicle_locations")
    op.drop_index(
        "idx_vehicle_locations_tenant_vehicle_recorded",
        table_name="vehicle_locations",
    )
    op.drop_table("vehicle_locations")
