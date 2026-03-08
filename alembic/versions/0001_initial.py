"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-03-08 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # make sure the UUID extension is available
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "saga_log",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # enable RLS and add tenant isolation policies
    op.execute("ALTER TABLE outbox_events ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY tenant_isolation ON outbox_events USING (tenant_id = current_setting('app.tenant_id')::uuid);"
    )
    op.execute("ALTER TABLE saga_log ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY tenant_isolation ON saga_log USING (tenant_id = current_setting('app.tenant_id')::uuid);"
    )


def downgrade():
    op.drop_table("saga_log")
    op.drop_table("outbox_events")
