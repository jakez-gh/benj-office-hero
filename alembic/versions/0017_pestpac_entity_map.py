"""PestPac entity map table (Slice 27)

Revision ID: 0017_pestpac_entity_map
Revises: 0016_jobber_tables
Create Date: 2026-06-18 00:00:00.000000

``pestpac_entity_map`` stores bidirectional mapping between our internal UUIDs
and PestPac's integer IDs (LocationCode for customers, WorkOrderId for jobs).
Required because the Odyssey API has no native externalId on either entity type.

Design blocker resolved before writing the HTTP adapter: confirm whether the
Odyssey API returns the created entity synchronously or returns a requestId
(async pattern like the WWRM sibling API).  See RES-026 open question #1.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0017_pestpac_entity_map"
down_revision = "0016_jobber_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pestpac_entity_map",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # 'location' (BillTo Location → Customer) or 'workorder' (Work Order → Job)
        sa.Column("entity_type", sa.String(20), nullable=False),
        sa.Column("internal_id", UUID(as_uuid=True), nullable=False),
        # PestPac integer ID stored as string to avoid overflow on very large tenants
        sa.Column("pestpac_id", sa.String(50), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "tenant_id", "entity_type", "internal_id", name="uq_pestpac_map_internal"
        ),
        sa.UniqueConstraint(
            "tenant_id", "entity_type", "pestpac_id", name="uq_pestpac_map_pestpac_id"
        ),
    )
    op.create_index(
        "idx_pestpac_entity_map_tenant_type_internal",
        "pestpac_entity_map",
        ["tenant_id", "entity_type", "internal_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_pestpac_entity_map_tenant_type_internal", table_name="pestpac_entity_map")
    op.drop_table("pestpac_entity_map")
