"""Create servicetitan_entity_map table for ST integer ID storage

Revision ID: 0015_servicetitan_entity_map
Revises: 0014_performance_indexes
Create Date: 2026-06-18 00:00:00.000000

Stores the mapping between our internal UUIDs and ServiceTitan's integer IDs
for customers and jobs.  Required because ST has no native externalId on the
customer entity; we use externalData at write time, but caching the integer ID
here avoids a round-trip externalData query on every update/delete.

Slice 26: ServiceTitan integration.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0015_servicetitan_entity_map"
down_revision = "0014_performance_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "servicetitan_entity_map",
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
        sa.Column("entity_type", sa.String(20), nullable=False),
        sa.Column("internal_id", UUID(as_uuid=True), nullable=False),
        sa.Column("st_id", sa.Integer, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("tenant_id", "entity_type", "internal_id", name="uq_st_map_internal"),
        sa.UniqueConstraint("tenant_id", "entity_type", "st_id", name="uq_st_map_st_id"),
    )
    op.create_index(
        "idx_st_entity_map_tenant_type_internal",
        "servicetitan_entity_map",
        ["tenant_id", "entity_type", "internal_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_st_entity_map_tenant_type_internal", table_name="servicetitan_entity_map")
    op.drop_table("servicetitan_entity_map")
