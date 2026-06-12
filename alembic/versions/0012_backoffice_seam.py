"""Back-office seam hardening: outbox/saga indexes + RLS, tenant adapter column (Slice 24)

Revision ID: 0012_backoffice_seam
Revises: 0011_contracts
Create Date: 2026-06-12 00:00:00.000000

* ``outbox_events``: + ``dead_letter_reason`` (protocol + admin UI already use it),
  index ``(tenant_id, status, created_at)`` for the pending-poll, RLS policy.
* ``saga_log``: + ``last_error``, index ``(tenant_id, saga_type)``, RLS policy.
* ``tenants``: + ``back_office_adapter`` (default ``native``) with CHECK on the
  known adapter registry names.
"""

import sqlalchemy as sa

from alembic import op

revision = "0012_backoffice_seam"
down_revision = "0011_contracts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("outbox_events", sa.Column("dead_letter_reason", sa.Text(), nullable=True))
    op.create_index(
        "idx_outbox_tenant_status_created",
        "outbox_events",
        ["tenant_id", "status", "created_at"],
    )
    op.execute(
        """
        ALTER TABLE outbox_events ENABLE ROW LEVEL SECURITY;
        CREATE POLICY outbox_tenant_isolation ON outbox_events
            USING (tenant_id = current_setting('app.tenant_id'));
        """
    )

    op.add_column("saga_log", sa.Column("last_error", sa.Text(), nullable=True))
    op.create_index("idx_saga_log_tenant_type", "saga_log", ["tenant_id", "saga_type"])
    op.execute(
        """
        ALTER TABLE saga_log ENABLE ROW LEVEL SECURITY;
        CREATE POLICY saga_log_tenant_isolation ON saga_log
            USING (tenant_id = current_setting('app.tenant_id'));
        """
    )

    op.add_column(
        "tenants",
        sa.Column(
            "back_office_adapter",
            sa.String(50),
            nullable=False,
            server_default="native",
        ),
    )
    op.create_check_constraint(
        "ck_tenant_back_office_adapter",
        "tenants",
        "back_office_adapter IN ('native','servicetitan','pestpac','jobber')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_tenant_back_office_adapter", "tenants", type_="check")
    op.drop_column("tenants", "back_office_adapter")

    op.execute("DROP POLICY IF EXISTS saga_log_tenant_isolation ON saga_log;")
    op.execute("ALTER TABLE saga_log DISABLE ROW LEVEL SECURITY;")
    op.drop_index("idx_saga_log_tenant_type", table_name="saga_log")
    op.drop_column("saga_log", "last_error")

    op.execute("DROP POLICY IF EXISTS outbox_tenant_isolation ON outbox_events;")
    op.execute("ALTER TABLE outbox_events DISABLE ROW LEVEL SECURITY;")
    op.drop_index("idx_outbox_tenant_status_created", table_name="outbox_events")
    op.drop_column("outbox_events", "dead_letter_reason")
