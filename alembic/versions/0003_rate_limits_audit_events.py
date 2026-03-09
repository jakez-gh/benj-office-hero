"""rate limits, ban list, and audit events tables

Revision ID: 0003_rate_limits_audit_events
Revises: 0002_users_and_tokens
Create Date: 2026-03-09 00:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_rate_limits_audit_events"
down_revision = "0002_users_and_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create rate_limits table
    op.create_table(
        "rate_limits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("limit", sa.Integer(), nullable=False),
        sa.Column("per_seconds", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(length=50), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=True),
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
    )

    # Create ban_list table (same schema as rate_limits but for denied entries)
    op.create_table(
        "ban_list",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("limit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("per_seconds", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("scope", sa.String(length=50), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=True),
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
    )

    # Create audit_events table (append-only, INSERT only via trigger)
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )

    # Index for efficient querying by tenant, event type, and time
    op.create_index(
        "ix_audit_events_tenant_type_ts",
        "audit_events",
        ["tenant_id", "event_type", "timestamp"],
    )

    # DB trigger to prevent UPDATE and DELETE on audit_events (append-only)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_audit_event_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events is append-only: UPDATE and DELETE are not permitted';
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER audit_events_immutable
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_event_modification();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_events_immutable ON audit_events;")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_event_modification();")
    op.drop_index("ix_audit_events_tenant_type_ts", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_table("ban_list")
    op.drop_table("rate_limits")
