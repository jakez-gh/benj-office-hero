"""Create routes and route_stops tables (Slice 14: dispatch & route management)

Revision ID: 0009_routes
Revises: 0008_vehicle_locations
Create Date: 2026-05-30 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

revision = "0009_routes"
down_revision = "0008_vehicle_locations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "routes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("vehicle_id", sa.UUID(), nullable=False),
        sa.Column("vehicle_crew_id", sa.UUID(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="committed"),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("total_distance_m", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_duration_s", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("option_kind_applied", sa.String(20), nullable=True),
        sa.Column("committed_by_user_id", sa.UUID(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], name="fk_routes_vehicle"),
        sa.ForeignKeyConstraint(
            ["vehicle_crew_id"], ["vehicle_crews.id"], name="fk_routes_vehicle_crew"
        ),
        sa.ForeignKeyConstraint(
            ["committed_by_user_id"], ["users.id"], name="fk_routes_committed_by_user"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "vehicle_id", "work_date", name="uq_route_tenant_vehicle_date"
        ),
        sa.CheckConstraint(
            "status IN ('draft','committed','in_progress','complete','cancelled')",
            name="ck_route_status",
        ),
    )
    op.create_index("idx_routes_tenant_work_date", "routes", ["tenant_id", "work_date"])
    op.create_index("idx_routes_tenant_status", "routes", ["tenant_id", "status"])

    op.create_table(
        "route_stops",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("route_id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("sequence_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("planned_eta", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_arrived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("planned_distance_from_prev_m", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("planned_duration_from_prev_s", sa.Integer(), nullable=False, server_default="0"),
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
        sa.ForeignKeyConstraint(
            ["route_id"], ["routes.id"], name="fk_stop_route", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], name="fk_stop_job"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("route_id", "sequence_index", name="uq_stop_route_sequence"),
        sa.UniqueConstraint("route_id", "job_id", name="uq_stop_route_job"),
        sa.CheckConstraint(
            "status IN ('pending','arrived','complete','skipped')",
            name="ck_stop_status",
        ),
    )
    op.create_index("idx_route_stops_tenant_route", "route_stops", ["tenant_id", "route_id"])


def downgrade() -> None:
    op.drop_index("idx_route_stops_tenant_route", table_name="route_stops")
    op.drop_table("route_stops")
    op.drop_index("idx_routes_tenant_status", table_name="routes")
    op.drop_index("idx_routes_tenant_work_date", table_name="routes")
    op.drop_table("routes")
