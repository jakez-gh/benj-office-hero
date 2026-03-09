"""users and tokens tables with RLS

Revision ID: 0002_users_and_tokens
Revises: 0001_initial
Create Date: 2026-03-08 20:00:00.000000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "0002_users_and_tokens"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    # Create tenants table
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
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

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
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
        sa.UniqueConstraint("tenant_id", "email", name="uq_tenant_email"),
    )

    # Create RLS policy for users table
    op.execute(
        """
        ALTER TABLE users ENABLE ROW LEVEL SECURITY;
        CREATE POLICY users_tenant_isolation ON users
            USING (tenant_id = current_setting('app.tenant_id')::uuid);
        """
    )

    # Create refresh_tokens table
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )

    # Create RLS policy for refresh_tokens via user's tenant
    op.execute(
        """
        ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY;
        CREATE POLICY refresh_tokens_tenant_isolation ON refresh_tokens
            USING (user_id IN (
                SELECT id FROM users WHERE tenant_id = current_setting('app.tenant_id')::uuid
            ));
        """
    )


def downgrade():
    op.execute("DROP POLICY IF EXISTS refresh_tokens_tenant_isolation ON refresh_tokens;")
    op.execute("ALTER TABLE refresh_tokens DISABLE ROW LEVEL SECURITY;")
    op.drop_table("refresh_tokens")

    op.execute("DROP POLICY IF EXISTS users_tenant_isolation ON users;")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY;")
    op.drop_table("users")

    op.drop_table("tenants")
