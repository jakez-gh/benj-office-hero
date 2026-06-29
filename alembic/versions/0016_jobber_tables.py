"""Jobber integration tables: credentials + entity map (Slice 28)

Revision ID: 0016_jobber_tables
Revises: 0015_servicetitan_entity_map
Create Date: 2026-06-18 00:00:00.000000

* ``jobber_credentials`` — per-tenant OAuth2 tokens (access + refresh) and
  optional custom-field config IDs discovered at first connect.
* ``jobber_entity_map`` — bidirectional mapping between our internal UUIDs and
  Jobber's opaque encoded IDs for both clients and jobs.
"""

import sqlalchemy as sa

from alembic import op

revision = "0016_jobber_tables"
down_revision = "0015_servicetitan_entity_map"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobber_credentials",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("custom_field_client_config_id", sa.Text(), nullable=True),
        sa.Column("custom_field_job_config_id", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("tenant_id", name="uq_jobber_credentials_tenant"),
    )

    op.create_table(
        "jobber_entity_map",
        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("entity_type", sa.String(10), nullable=False),
        sa.Column("internal_id", sa.UUID(), nullable=False),
        sa.Column("jobber_id", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "entity_type",
            "internal_id",
            name="uq_jobber_entity_map_internal",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "entity_type",
            "jobber_id",
            name="uq_jobber_entity_map_jobber",
        ),
    )


def downgrade() -> None:
    op.drop_table("jobber_entity_map")
    op.drop_table("jobber_credentials")
